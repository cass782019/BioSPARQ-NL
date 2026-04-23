"""Backends de LLM: LM Studio (OpenAI-compat), Anthropic SDK, Claude CLI subprocess."""
import logging
import os
import shutil
import subprocess
import time

logger = logging.getLogger(__name__)


def _resolve_lm_studio_model(base_url: str, requested: str) -> str:
    """If requested is 'auto' or empty, return the first non-embedding model
    currently loaded in LM Studio. Otherwise return requested as-is."""
    if requested and requested.lower() != "auto":
        return requested
    try:
        import requests as _req
        resp = _req.get(f"{base_url}/models", timeout=5)
        resp.raise_for_status()
        models = resp.json().get("data", [])
        for m in models:
            mid = m.get("id", "")
            if "embed" not in mid.lower():
                logger.info("LM Studio auto-selected model: %s", mid)
                return mid
    except Exception as e:
        logger.warning("Could not auto-detect LM Studio model: %s", e)
    return requested or "auto"


class LMStudioBackend:
    """Backend para LM Studio via API OpenAI-compatible."""

    def __init__(self, config):
        from openai import OpenAI

        base_url = config["lm_studio_url"]
        self.client = OpenAI(
            base_url=base_url,
            api_key="lm-studio",
            timeout=config.get("llm_timeout", 120.0),
        )
        self.model = _resolve_lm_studio_model(base_url, config["llm_model"])

    def generate(self, system: str, user_msg: str) -> str:
        from openai import APITimeoutError, APIConnectionError

        # Modelos de raciocinio (Nemotron, o1-like) consomem tokens em reasoning_content
        # antes de emitir content. Permite override via env var.
        max_tokens = int(os.getenv("LLM_MAX_TOKENS", "3000"))

        for attempt in range(3):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_msg},
                    ],
                    temperature=0.1,
                    max_tokens=max_tokens,
                    extra_body={"thinking": {"type": "disabled"}},
                )
                msg = response.choices[0].message
                content = msg.content or ""
                # Modelos de raciocinio (Nemotron, o1-like) retornam content vazio
                # e colocam o output em reasoning_content. O SDK OpenAI v2 guarda
                # campos extras em model_extra, nao como atributos diretos.
                if not content.strip():
                    reasoning = (
                        getattr(msg, "reasoning_content", None)
                        or (msg.model_extra or {}).get("reasoning_content", "")
                    ) or ""
                    if reasoning:
                        content = reasoning
                return content
            except APIConnectionError:
                if attempt < 2:
                    time.sleep(2 ** (attempt + 1))
                    continue
                raise
            except APITimeoutError:
                if attempt < 2:
                    time.sleep(2 ** (attempt + 1))
                    continue
                raise


class AnthropicBackend:
    """Backend para Claude via Anthropic SDK."""

    def __init__(self, config):
        import anthropic

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not set. Export it or add to .env file."
            )
        self.client = anthropic.Anthropic(
            api_key=api_key,
            timeout=config.get("llm_timeout", 120.0),
        )
        self.model = config["llm_model"]

    def generate(self, system: str, user_msg: str) -> str:
        for attempt in range(3):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1000,
                    temperature=0.1,
                    system=system,
                    messages=[{"role": "user", "content": user_msg}],
                )
                return response.content[0].text
            except Exception as e:
                if attempt < 2 and "overloaded" in str(e).lower():
                    time.sleep(2 ** (attempt + 1))
                    continue
                raise


class ClaudeCLIBackend:
    """Backend para Claude via `claude` CLI em modo --print.

    Reutiliza a sessao OAuth do Claude Code ja autenticada no browser — nao
    precisa de ANTHROPIC_API_KEY. Isolamos o benchmark assim:
    - cwd: diretorio temporario fora de proj1 (evita auto-discovery de CLAUDE.md)
    - --system-prompt: substitui o prompt padrao do Claude Code
    - --disable-slash-commands: desabilita skills
    - stdin: user_msg passado via input (evita limites de arg no Windows)
    """

    def __init__(self, config):
        if shutil.which("claude") is None:
            raise RuntimeError("claude CLI not found in PATH")
        self.model = config.get("llm_model", "sonnet")
        self.timeout = int(config.get("llm_timeout", 300))
        self.max_budget = config.get("max_budget_usd")
        self.workdir = os.path.expanduser("~/.biosparql-bench-workdir")
        os.makedirs(self.workdir, exist_ok=True)

    def generate(self, system: str, user_msg: str) -> str:
        cmd = [
            "claude",
            "--print",
            "--model", self.model,
            "--system-prompt", system,
            "--output-format", "text",
            "--input-format", "text",
            "--disable-slash-commands",
        ]
        if self.max_budget is not None:
            cmd += ["--max-budget-usd", str(self.max_budget)]

        try:
            result = subprocess.run(
                cmd,
                input=user_msg,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
                check=False,
                cwd=self.workdir,
            )
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"claude CLI timeout after {self.timeout}s") from e

        if result.returncode != 0:
            err = (result.stderr or "").strip()[:500]
            raise RuntimeError(f"claude CLI failed (code {result.returncode}): {err}")
        return result.stdout


class HuggingFaceBackend:
    """Backend para modelos HuggingFace locais via transformers pipeline.

    Suporta dois modos:
    - GPT-2 style (BioMedLM, BioGPT): text continuation, sem chat template
    - Instruct (config["hf_instruct"]=True): usa apply_chat_template
    """

    def __init__(self, config):
        from transformers import pipeline as hf_pipeline

        model_id = config["llm_model"]
        self.is_instruct = config.get("hf_instruct", False)
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "512"))
        offload_folder = config.get(
            "hf_offload_folder",
            os.path.expanduser("~/.biosparql-hf-offload"),
        )
        os.makedirs(offload_folder, exist_ok=True)
        logger.info("Carregando modelo HuggingFace: %s", model_id)
        self.pipe = hf_pipeline(
            "text-generation",
            model=model_id,
            device_map="auto",
            dtype="auto",
            model_kwargs={"offload_folder": offload_folder},
        )
        self.tokenizer = self.pipe.tokenizer

    def generate(self, system: str, user_msg: str) -> str:
        if self.is_instruct and hasattr(self.tokenizer, "apply_chat_template"):
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ]
            prompt = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        else:
            # GPT-2 style: text continuation sem roles
            prompt = f"{system}\n\nQuestion: {user_msg}\n\nSPARQL query:"

        result = self.pipe(
            prompt,
            max_new_tokens=self.max_tokens,
            temperature=0.1,
            do_sample=True,
            return_full_text=False,
        )
        return result[0]["generated_text"]


def create_backend(config):
    """Factory: cria o backend apropriado baseado na config."""
    backend_type = config.get("backend") or os.getenv("BACKEND", "lm_studio")
    if backend_type == "claude_cli":
        return ClaudeCLIBackend(config)
    if backend_type == "anthropic":
        return AnthropicBackend(config)
    if backend_type == "huggingface":
        return HuggingFaceBackend(config)
    return LMStudioBackend(config)

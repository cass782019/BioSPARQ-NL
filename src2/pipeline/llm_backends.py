"""Backends de LLM (revisao 2): LM Studio (OpenAI-compat) e Claude via CLI subprocess.

ClaudeCLIBackend usa o `claude` CLI em modo --print para reutilizar a autenticacao
OAuth do Claude Code ja existente no notebook - nao precisa de ANTHROPIC_API_KEY.
"""
import logging
import os
import shutil
import subprocess
import time

logger = logging.getLogger(__name__)


class LMStudioBackend:
    """Backend para LM Studio via API OpenAI-compatible."""

    def __init__(self, config):
        from openai import OpenAI

        self.client = OpenAI(
            base_url=config["lm_studio_url"],
            api_key="lm-studio",
            timeout=config.get("llm_timeout", 120.0),
        )
        self.model = config["llm_model"]

    def generate(self, system: str, user_msg: str) -> str:
        from openai import APITimeoutError, APIConnectionError

        for attempt in range(3):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_msg},
                    ],
                    temperature=0.1,
                    max_tokens=1000,
                )
                return response.choices[0].message.content
            except (APIConnectionError, APITimeoutError):
                if attempt < 2:
                    time.sleep(2 ** (attempt + 1))
                    continue
                raise


class ClaudeCLIBackend:
    """Backend para Claude via `claude` CLI em modo --print.

    Reutiliza a sessao OAuth do Claude Code ja autenticada no browser.

    NOTA: --bare NAO eh usado porque ele bloqueia OAuth (le apenas ANTHROPIC_API_KEY).
    Em vez disso, isolamos o benchmark assim:
    - cwd: diretorio temporario fora de proj1 (evita descobrir CLAUDE.md do projeto)
    - --system-prompt: substitui o prompt padrao do Claude Code com o nosso
    - --disable-slash-commands: desabilita skills
    - stdin: user_msg passado via input (evita limites de arg no Windows)
    """

    def __init__(self, config):
        if shutil.which("claude") is None:
            raise RuntimeError("claude CLI not found in PATH")
        self.model = config.get("llm_model", "sonnet")
        self.timeout = int(config.get("llm_timeout", 180))
        self.max_budget = config.get("max_budget_usd")

        # Diretorio isolado fora de proj1 para evitar auto-discovery de CLAUDE.md
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


def create_backend(config):
    """Factory: cria o backend apropriado baseado na config."""
    backend_type = config.get("backend", "lm_studio")
    if backend_type == "claude_cli":
        return ClaudeCLIBackend(config)
    return LMStudioBackend(config)

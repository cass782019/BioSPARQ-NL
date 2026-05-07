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


class CodexCLIBackend:
    """Backend para ChatGPT/Codex via `codex exec` CLI.

    Usa --output-last-message para extrair apenas a resposta (sem metadados).
    Reutiliza a sessao OAuth do ChatGPT ja autenticada via `codex login`.
    """

    def __init__(self, config):
        # No Windows o npm gera codex.cmd; resolver para o executavel real
        self.cli_path = shutil.which("codex.cmd") or shutil.which("codex")
        if self.cli_path is None:
            raise RuntimeError("codex CLI not found in PATH")
        self.model = config.get("llm_model", "gpt-5.5")
        self.timeout = int(config.get("llm_timeout", 180))
        self.workdir = os.path.expanduser("~/.biosparql-bench-workdir")
        os.makedirs(self.workdir, exist_ok=True)

    def generate(self, system: str, user_msg: str) -> str:
        import tempfile
        import re

        # Codex (gpt-5.5) tende a ser conversacional - usar role-play forte
        combined = (
            "You are a SPARQL query generator. You MUST respond with ONLY the SPARQL query "
            "and nothing else. Start with PREFIX or SELECT. End with the closing }. "
            "Do not add explanations, do not greet, do not ask questions, do not use markdown. "
            "If you write any non-SPARQL text the system will reject your output.\n\n"
            f"--- CONTEXT ---\n{system}\n\n--- TASK ---\n{user_msg}\n\n"
            "Output the complete SPARQL query now:"
        )

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt", encoding="utf-8"
        ) as tf:
            output_file = tf.name

        try:
            cmd = [
                self.cli_path, "exec",
                "--skip-git-repo-check",
                "--ephemeral",
                "--sandbox", "read-only",
                "--color", "never",
                "--output-last-message", output_file,
                "-C", self.workdir,
                "-m", self.model,
                combined,
            ]
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=self.timeout,
                    check=False,
                )
            except subprocess.TimeoutExpired as e:
                raise RuntimeError(f"codex CLI timeout after {self.timeout}s") from e

            if result.returncode != 0:
                err = (result.stderr or "").strip()[:500]
                raise RuntimeError(
                    f"codex CLI failed (code {result.returncode}): {err}"
                )

            with open(output_file, encoding="utf-8") as f:
                raw = f.read()
        finally:
            try:
                os.unlink(output_file)
            except OSError:
                pass

        return self._extract_sparql_aggressive(raw)

    @staticmethod
    def _extract_sparql_aggressive(raw: str) -> str:
        """Extrai SPARQL de resposta conversacional do Codex.

        Estrategia:
        1. Markdown fence (```sparql ou ```)
        2. Bloco contiguo iniciando com PREFIX/SELECT/CONSTRUCT/DESCRIBE/ASK
           ate ultima '}' equilibrada
        """
        import re

        # 1. Markdown fences
        if "```sparql" in raw:
            inner = raw.split("```sparql", 1)[1].split("```", 1)[0]
            if inner.strip():
                return inner.strip()
        if "```" in raw:
            inner = raw.split("```", 1)[1].split("```", 1)[0]
            if inner.strip() and re.search(r"\b(SELECT|ASK|CONSTRUCT|DESCRIBE|PREFIX)\b", inner, re.IGNORECASE):
                return inner.strip()

        # 2. Localizar inicio do SPARQL
        m = re.search(r"\b(PREFIX\s+\w+\s*:|SELECT\s|ASK\s|CONSTRUCT\s|DESCRIBE\s)", raw, re.IGNORECASE)
        if not m:
            return raw.strip()
        start = m.start()

        # 3. Coletar linhas que parecem SPARQL ate detectar texto conversacional
        sparql_keywords = re.compile(
            r"^\s*(PREFIX|SELECT|ASK|CONSTRUCT|DESCRIBE|WHERE|FILTER|OPTIONAL|GRAPH|"
            r"BIND|UNION|MINUS|GROUP|HAVING|ORDER|LIMIT|OFFSET|VALUES|SERVICE|"
            r"\?|\}|\{|\#|\<|\".*?\"|\.|\;)",
            re.IGNORECASE,
        )
        lines = raw[start:].splitlines()
        out_lines = []
        depth = 0
        for ln in lines:
            stripped = ln.strip()
            # Linha em branco e ok
            if not stripped:
                out_lines.append(ln)
                continue
            # Detecta linha conversacional (frase em pt/en sem sintaxe SPARQL)
            if depth == 0 and not sparql_keywords.match(stripped) and re.match(r"^[A-Za-zÀ-ÿ]+\s+[A-Za-zÀ-ÿ]", stripped):
                # Provavel texto conversacional - parar
                break
            out_lines.append(ln)
            depth += stripped.count("{") - stripped.count("}")
            # Se equilibrou e ja teve abertura, encerra
            if depth == 0 and "}" in stripped and any("{" in l for l in out_lines):
                break
        return "\n".join(out_lines).strip()


class GeminiCLIBackend:
    """Backend para Gemini via `gemini -p` CLI em modo headless."""

    def __init__(self, config):
        self.cli_path = shutil.which("gemini.cmd") or shutil.which("gemini")
        if self.cli_path is None:
            raise RuntimeError("gemini CLI not found in PATH")
        self.model = config.get("llm_model")  # opcional - usa default do CLI se None
        self.timeout = int(config.get("llm_timeout", 180))
        self.workdir = os.path.expanduser("~/.biosparql-bench-workdir")
        os.makedirs(self.workdir, exist_ok=True)

    def generate(self, system: str, user_msg: str) -> str:
        # Gemini nao tem --system-prompt: combina em um unico prompt
        combined = f"{system}\n\n{user_msg}"

        cmd = [self.cli_path, "-p", combined, "--skip-trust", "--approval-mode", "plan"]
        if self.model:
            cmd += ["-m", self.model]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
                check=False,
                cwd=self.workdir,
            )
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"gemini CLI timeout after {self.timeout}s") from e

        if result.returncode != 0:
            err = (result.stderr or "").strip()[:500]
            raise RuntimeError(
                f"gemini CLI failed (code {result.returncode}): {err}"
            )
        return result.stdout


def create_backend(config):
    """Factory: cria o backend apropriado baseado na config."""
    backend_type = config.get("backend", "lm_studio")
    if backend_type == "claude_cli":
        return ClaudeCLIBackend(config)
    if backend_type == "codex_cli":
        return CodexCLIBackend(config)
    if backend_type == "gemini_cli":
        return GeminiCLIBackend(config)
    return LMStudioBackend(config)

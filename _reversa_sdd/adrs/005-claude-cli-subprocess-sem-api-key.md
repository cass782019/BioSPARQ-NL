# ADR-005 — ClaudeCLIBackend via subprocess em vez de Anthropic SDK com API key

> Data: 2026-05-04 (retroativo — extraído da estrutura src2 e CLAUDE.md)
> Status: **Aceito** (em src2)
> Confiança: 🟢 CONFIRMADO — documentado no CLAUDE.md e confirmado pelo código em `src2/pipeline/llm_backends.py`

---

## Contexto

Para avaliar o modelo Claude Sonnet no benchmark sem expor a `ANTHROPIC_API_KEY`, duas abordagens foram avaliadas:

- **Anthropic SDK** — `anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))`
- **Claude CLI subprocess** — `subprocess.run(["claude", "--print", "--model", ..., "--disable-slash-commands"])`

O CLI do Claude Code já está autenticado via OAuth na sessão ativa — não requer API key.

## Decisão

Implementar `ClaudeCLIBackend` em `src2/pipeline/llm_backends.py` que:
1. Invoca `claude` CLI via `subprocess.run()` com `--print` (modo não-interativo)
2. Passa o system prompt via `--system-prompt` e o user message via stdin
3. Roda em diretório temporário `~/.biosparql-bench-workdir` para evitar auto-discovery do `CLAUDE.md` de proj1
4. Usa `--disable-slash-commands` para isolamento
5. Timeout explícito de 180s (configurável)

## Alternativas consideradas

| Alternativa | Resultado | Motivo da rejeição |
|---|---|---|
| Anthropic SDK com `ANTHROPIC_API_KEY` | Funciona (usado em src/) | Requer exposição de credencial; custo por token |
| Claude CLI sem isolamento de diretório | Funciona mas descobre CLAUDE.md | Contaminação do contexto com instruções do projeto |
| Manter apenas LM Studio para todos os modelos | Sem Claude no benchmark | Claude Sonnet é o "upper bound" do paper — essencial para comparação |

## Consequências

- `src2/` pode rodar Claude Sonnet sem `ANTHROPIC_API_KEY` em máquinas com Claude Code autenticado
- Acoplamento à sessão OAuth do Claude Code — exige que o usuário esteja logado no Claude Code na mesma máquina
- Subprocesso é mais lento que SDK direto (overhead de spawn + I/O via pipes)
- Diretório de isolamento `~/.biosparql-bench-workdir` é criado automaticamente
- Input via stdin evita limites de tamanho de argumento no Windows (relevante para system prompts longos)
- `--max-budget-usd N` pode ser usado para limitar gastos por run (🟡 INFERIDO — parâmetro mencionado no CLAUDE.md mas uso condicional no código)

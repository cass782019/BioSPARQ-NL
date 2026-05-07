# Perguntas em Aberto — gates

> Unit: `gates/` | Gerado pelo Redator em 2026-05-04
> Estas perguntas requerem validação humana — não podem ser respondidas apenas com análise de código.

---

## Q-GATES-01 — Os thresholds de gate2 são bugs ou o gold standard foi expandido?

**Confiança:** 🔴 LACUNA

**Contexto:**  
`gates/gate2_check.py` exige `len(qs) >= 50` e `index.ntotal >= 50`, mas o gold standard em `data/gold_standard/questions.json` tem **30 questões**.

**Pergunta:**  
Há planos de expandir o gold standard para 50+ questões? Os thresholds de 50 foram escritos antecipando essa expansão, ou são simplesmente bugs (deveria ser 30)?

**Impacto da resposta:**  
- Se bug → corrigir para `>= 30` imediatamente (TASK-GATES-02)  
- Se planejado → documentar roadmap e deixar threshold como está temporariamente  

---

## Q-GATES-02 — Gate4 e Gate5 foram planejados para quê?

**Confiança:** 🔴 LACUNA

**Contexto:**  
A sequência de gates é `0, 1, 2, 3, 6`. Os números 4 e 5 estão ausentes. Não há comentários no código ou documentação explicando.

**Pergunta:**  
Quais verificações eram/são previstas para gate4 e gate5? Foram implementados e depois removidos? Ou reservados para fases futuras (ex.: gate4 = avaliação formal, gate5 = ablação)?

**Impacto da resposta:**  
- Se reservados → documentar propósito em `gates/README.md`  
- Se descartados → pode renumerar para sequência contínua 0-4 na reimplementação  

---

## Q-GATES-03 — O threshold leniente do gate3 (1/3) ainda é adequado?

**Confiança:** 🟡 INFERIDO

**Contexto:**  
```python
gate_pass = passed_questions >= 1  # At least 1/3 with current small model
```
O comentário indica que o threshold foi ajustado para modelos 4B. Com os resultados de avaliação (Nemotron 4B: 80%, Qwen 9B: 50%), o sistema demonstrou desempenho superior ao esperado na época de escrita.

**Pergunta:**  
O threshold de 1/3 ainda é o correto para gate3, ou deve ser elevado para 2/3 ou 100% agora que os modelos foram avaliados formalmente?

**Impacto da resposta:**  
- Threshold mais alto → gate3 mais rigoroso, requer LLM de melhor qualidade para passar  
- Threshold atual → gate3 funciona como "smoke test" mínimo, não como validação de qualidade  

---

## Q-GATES-04 — O gate6 deve testar o servidor real ou o TestClient é suficiente?

**Confiança:** 🟡 INFERIDO

**Contexto:**  
Gate6 usa `fastapi.testclient.TestClient` (ASGI in-process), que não sobe um servidor HTTP real. Um servidor com problema de configuração de porta, certificado, ou middleware de CORS poderia passar no gate6 mas falhar em produção.

**Pergunta:**  
Para o contexto deste projeto (pesquisa acadêmica, uso local), o TestClient é suficiente? Ou seria útil adicionar um check de servidor real (`uvicorn` em subprocess + `requests.get`)?

**Impacto da resposta:**  
- TestClient suficiente → manter gate6 como está  
- Servidor real necessário → adicionar seção em gate6 que sobe uvicorn em porta alternativa e testa via requests  

---

## Q-GATES-05 — Deve existir um check de ambiente para Anthropic API key?

**Confiança:** 🔴 LACUNA

**Contexto:**  
O sistema suporta dois backends: LM Studio (local) e Anthropic API (via `ANTHROPIC_API_KEY`). Gate0 não verifica se `ANTHROPIC_API_KEY` está configurada quando o backend Anthropic é desejado.

**Pergunta:**  
Gate0 deve verificar `os.environ.get("ANTHROPIC_API_KEY")` e reportar como aviso (não falha) se ausente? Ou assume-se que quem usa Anthropic sabe configurar a key?

**Impacto da resposta:**  
- Adicionar check → gate0 mais informativo para novos usuários  
- Não adicionar → manter gate0 focado apenas em ambiente local (LM Studio)  

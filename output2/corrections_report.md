# BioSPARQL-NL: Relatorio de Correcoes

**Baseline:** 24/52 (46.2%)
**Corrigido:** 30/52 (57.7%)
**Delta:** +6 questoes (+11.5 pp)

## Por dificuldade

| Dificuldade | Baseline | Corrigido | Delta |
|-------------|----------|-----------|-------|
| easy | 9/13 (69%) | 10/13 (77%) | +1 |
| medium | 9/18 (50%) | 13/18 (72%) | +4 |
| hard | 6/21 (29%) | 7/21 (33%) | +1 |

## Categorias de falha

| Categoria | Baseline | Corrigido |
|-----------|----------|-----------|
| syntax_error | 3 | 5 |
| timeout_or_exception | 1 | 0 |
| zero_results | 24 | 17 |

## Questoes recuperadas (11)

- **Q11**: Quais doenças estão associadas ao fenótipo 'aracnodactilia'?
- **Q13**: Quais doenças OMIM estão associadas ao fenótipo 'Intellectual disabili
- **Q14**: Quais fenótipos estão associados à doença com xref OMIM:154700 no DOID
- **Q21**: Quais doenças genéticas do DOID possuem mais de 10 fenótipos anotados 
- **Q26**: Quais doenças do DOID não possuem nenhum fenótipo anotado no HPOA?
- **Q33**: Quais doenças OMIM no HPOA possuem anotações de fenótipo, mas cujo xre
- **Q35**: Quais são os labels de 'asthma' tanto no DOID quanto no HPO?
- **Q42**: Quais fenótipos aparecem em mais de 50 doenças no HPOA e são subclasse
- **Q43**: Quais são os termos HPO que são subclasse direta ou indireta de 'Abnor
- **Q47**: Quais doenças no DOID são subclasse de 'doença genética', possuem fenó
- **Q48**: Para cada doença no DOID com xref MIM, quantos fenótipos anotados no H

## Questoes que regrediram (5)

- **Q05**: Quais são os sinônimos de 'diabetes mellitus' no DOID?
  - erro: `zero_results`
- **Q15**: Quais subclasses de 'doença infecciosa' no DOID possuem definição?
  - erro: `zero_results`
- **Q29**: Qual é a distribuição de fenótipos por categoria raiz do HPO?
  - erro: `zero_results`
- **Q38**: Quais doenças possuem fenótipos anotados no HPOA que são subclasse de 
  - erro: `SYNTAX_ERROR: Expected SelectQuery, found 'UNION'  (at char 412), (line:14, col:3)`
- **Q46**: Quais fenótipos HPO são alcançáveis por um caminho de subClassOf segui
  - erro: `SYNTAX_ERROR: Expected SelectQuery, found 'WHERE'  (at char 494), (line:16, col:3)`

## Ainda falhando (17)

`Q06, Q09, Q16, Q20, Q23, Q25, Q27, Q28, Q30, Q32, Q39, Q40, Q41, Q45, Q49, Q51, Q52`

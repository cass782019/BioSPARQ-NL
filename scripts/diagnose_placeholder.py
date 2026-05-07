"""Diagnostico: contar ocorrencias de 'termo_ingles' nas queries geradas pelo full pipeline."""
import json
import sys
import os

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
os.environ['PYTHONUNBUFFERED'] = '1'

from src.pipeline.nl_to_sparql import BioSPARQLPipeline

LOG_PATH = 'output/placeholder_diagnostic.json'
INCREMENTAL_PATH = 'output/placeholder_diagnostic.partial.jsonl'


def main():
    qs = json.load(open('data/gold_standard/questions.json'))[:30]

    base = {
        'endpoint': 'http://localhost:3030/biomedical/sparql',
        'lm_studio_url': 'http://localhost:1234/v1',
        'llm_model': 'nvidia/nemotron-3-nano-4b',
        'backend': 'lm_studio',
        'max_retries': 2,
        'top_k_examples': 3,
        'llm_timeout': 180.0,
        'fuseki_timeout': 30,
    }

    print(f'[INIT] Iniciando diagnostico com {len(qs)} questoes', flush=True)
    pipeline = BioSPARQLPipeline(base)
    print(f'[INIT] Pipeline carregado', flush=True)

    placeholder_count = 0
    correct_count = 0
    results = []

    # Limpa log incremental
    open(INCREMENTAL_PATH, 'w').close()

    for i, q in enumerate(qs, 1):
        try:
            r = pipeline.run(q['question_en'])
            sparql = r.get('sparql', '')
            has_placeholder = 'termo_ingles' in sparql
            ok = r.get('execution', {}).get('count', 0) >= q.get('expected_min_results', 1)
            attempts = r.get('attempts')
        except Exception as e:
            sparql = ''
            has_placeholder = False
            ok = False
            attempts = 0
            print(f'[{i}/30] {q["id"]}: EXCECAO {e}', flush=True)

        if has_placeholder:
            placeholder_count += 1
        if ok:
            correct_count += 1

        entry = {
            'id': q['id'],
            'difficulty': q.get('difficulty'),
            'placeholder': has_placeholder,
            'correct': ok,
            'attempts': attempts,
            'sparql_snippet': sparql[:200] if has_placeholder else '',
        }
        results.append(entry)

        with open(INCREMENTAL_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

        print(f'[{i}/30] {q["id"]} [{q.get("difficulty")}]: placeholder={has_placeholder} correct={ok} attempts={attempts}', flush=True)

    print(flush=True)
    print(f'=== RESULTADO ===', flush=True)
    print(f'Placeholder presente: {placeholder_count}/30 ({placeholder_count/30:.1%})', flush=True)
    print(f'Corretas: {correct_count}/30 ({correct_count/30:.1%})', flush=True)

    with open(LOG_PATH, 'w', encoding='utf-8') as f:
        json.dump({
            'placeholder_count': placeholder_count,
            'correct_count': correct_count,
            'results': results,
        }, f, indent=2, ensure_ascii=False)

    print(f'[DONE] Salvo em {LOG_PATH}', flush=True)


if __name__ == '__main__':
    main()

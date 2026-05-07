"""Diagnostico: capturar SPARQL gerado e erros para analise qualitativa."""
import json
import sys
import os

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
os.environ['PYTHONUNBUFFERED'] = '1'

from src.pipeline.nl_to_sparql import BioSPARQLPipeline

LOG = 'output/error_diagnostic.jsonl'


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

    print(f'[INIT] {len(qs)} questoes', flush=True)
    pipeline = BioSPARQLPipeline(base)
    print(f'[INIT] Pipeline OK', flush=True)

    open(LOG, 'w').close()

    for i, q in enumerate(qs, 1):
        try:
            r = pipeline.run(q['question_en'], question_id=q['id'])
        except Exception as e:
            r = {'sparql':'', 'validation':{'valid':False,'errors':[{'message':str(e)}]}, 'execution':{'success':False,'count':0,'error':str(e)}, 'attempts':0}

        sparql = r.get('sparql','')
        val = r.get('validation', {})
        exe = r.get('execution', {})
        valid = val.get('valid', False)
        exec_ok = exe.get('success', False)
        count = exe.get('count', 0)
        ok = count >= q.get('expected_min_results', 1)

        entry = {
            'id': q['id'],
            'difficulty': q.get('difficulty'),
            'question': q['question_en'],
            'gold_sparql': q.get('sparql', '')[:300],
            'generated_sparql': sparql,
            'valid': valid,
            'val_errors': val.get('errors', []),
            'val_warnings': val.get('warnings', []),
            'exec_ok': exec_ok,
            'exec_error': exe.get('error', ''),
            'count': count,
            'expected_min': q.get('expected_min_results', 1),
            'meets_expected': ok,
            'attempts': r.get('attempts', 0),
        }

        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

        status = 'OK' if ok else ('VAL_FAIL' if not valid else ('EXEC_FAIL' if not exec_ok else 'NO_RESULTS'))
        print(f'[{i}/30] {q["id"]} [{q["difficulty"]}]: {status} attempts={r.get("attempts")}', flush=True)

    print(f'[DONE] Salvo em {LOG}', flush=True)


if __name__ == '__main__':
    main()

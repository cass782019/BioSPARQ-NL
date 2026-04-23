"""Gera fragmentos LaTeX (revisao 2) - le de output2/, escreve output2/tables/."""
import json
import os

INPUT_DIR = "output2"
OUTPUT_TABLES_DIR = "output2/tables"


def generate_ablation_table(ablation_data: dict) -> str:
    model = ablation_data.get("model", "?")
    ablations = ablation_data.get("ablations", {})

    rows = []
    for config_name, data in ablations.items():
        m = data["metrics"]
        label = data["label"]
        rows.append(
            f"    {label:<20} & "
            f"{m.get('syntactic_rate', 0):.1%} & "
            f"{m.get('execution_rate', 0):.1%} & "
            f"{m.get('correctness_rate', 0):.1%} & "
            f"{m.get('avg_time_seconds', 0):.1f}s & "
            f"{m.get('avg_attempts', 0):.2f} \\\\"
        )

    body = "\n".join(rows)
    return f"""\\begin{{table}}[H]
\\centering
\\caption{{Estudo de abla\\c{{c}}\\~{{a}}o ({model}).}}
\\label{{tab:ablacao}}
\\small
\\begin{{tabular}}{{lccccc}}
\\toprule
\\textbf{{Configura\\c{{c}}\\~{{a}}o}} & \\textbf{{Sint.}} & \\textbf{{Exec.}} & \\textbf{{Corre\\c{{c}}\\~{{a}}o}} & \\textbf{{Tempo}} & \\textbf{{Tent.}} \\\\
\\midrule
{body}
\\bottomrule
\\end{{tabular}}
\\end{{table}}"""


def generate_model_comparison_table(eval_files: list) -> str:
    rows = []
    for path in eval_files:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        model = data["model"]
        m = data["scenario_a_with_validation"]["metrics"]
        mc = data.get("scenario_c_zero_shot", {}).get("metrics", {})

        rows.append(
            f"    {model:<30} & "
            f"{m.get('syntactic_rate', 0):.1%} & "
            f"{m.get('execution_rate', 0):.1%} & "
            f"{m.get('correctness_rate', 0):.1%} & "
            f"{mc.get('correctness_rate', 0):.1%} & "
            f"{m.get('avg_time_seconds', 0):.1f}s \\\\"
        )

    body = "\n".join(rows)
    return f"""\\begin{{table}}[H]
\\centering
\\caption{{Compara\\c{{c}}\\~{{a}}o multi-modelo (com valida\\c{{c}}\\~{{a}}o vs zero-shot).}}
\\label{{tab:multimodelo_v2}}
\\small
\\begin{{tabular}}{{lccccc}}
\\toprule
\\textbf{{Modelo}} & \\textbf{{Sint.}} & \\textbf{{Exec.}} & \\textbf{{Corre\\c{{c}}\\~{{a}}o}} & \\textbf{{Zero-shot}} & \\textbf{{Tempo}} \\\\
\\midrule
{body}
\\bottomrule
\\end{{tabular}}
\\end{{table}}"""


def main():
    os.makedirs(OUTPUT_TABLES_DIR, exist_ok=True)

    # Ablation tables
    if os.path.isdir(INPUT_DIR):
        for f in sorted(os.listdir(INPUT_DIR)):
            if f.startswith("ablation_") and f.endswith(".json"):
                path = os.path.join(INPUT_DIR, f)
                with open(path, encoding="utf-8") as fh:
                    data = json.load(fh)
                table = generate_ablation_table(data)
                out = os.path.join(OUTPUT_TABLES_DIR, f.replace(".json", ".tex"))
                with open(out, "w", encoding="utf-8") as fh:
                    fh.write(table)
                print(f"[OK] {out}")

        # Model comparison table
        eval_files = sorted(
            os.path.join(INPUT_DIR, f)
            for f in os.listdir(INPUT_DIR)
            if f.startswith("eval_") and f.endswith(".json")
        )
        if eval_files:
            table = generate_model_comparison_table(eval_files)
            out = os.path.join(OUTPUT_TABLES_DIR, "model_comparison.tex")
            with open(out, "w", encoding="utf-8") as fh:
                fh.write(table)
            print(f"[OK] {out}")


if __name__ == "__main__":
    main()

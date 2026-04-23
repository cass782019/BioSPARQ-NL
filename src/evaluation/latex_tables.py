"""Gera fragmentos LaTeX para inclusao direta no paper."""
import json
import os


def generate_ablation_table(ablation_data: dict) -> str:
    """Gera tabela LaTeX de ablacao a partir de ablation_{model}.json."""
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
    """Gera tabela multi-modelo a partir de lista de eval_{model}.json."""
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
    os.makedirs("output/tables", exist_ok=True)

    # Ablation tables
    for f in sorted(os.listdir("output")):
        if f.startswith("ablation_") and f.endswith(".json"):
            path = os.path.join("output", f)
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            table = generate_ablation_table(data)
            out = os.path.join("output/tables", f.replace(".json", ".tex"))
            with open(out, "w", encoding="utf-8") as fh:
                fh.write(table)
            print(f"[OK] {out}")

    # Model comparison table
    eval_files = sorted(
        os.path.join("output", f)
        for f in os.listdir("output")
        if f.startswith("eval_") and f.endswith(".json")
    )
    if eval_files:
        table = generate_model_comparison_table(eval_files)
        out = "output/tables/model_comparison.tex"
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(table)
        print(f"[OK] {out}")


if __name__ == "__main__":
    main()

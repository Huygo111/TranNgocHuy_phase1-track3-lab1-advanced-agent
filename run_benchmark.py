from __future__ import annotations
import json
from pathlib import Path
import typer
from rich import print
from rich.progress import track
from src.reflexion_lab.agents import ReActAgent, ReflexionAgent
from src.reflexion_lab.reporting import build_report, save_report
from src.reflexion_lab.utils import load_dataset, save_jsonl
app = typer.Typer(add_completion=False)

@app.command()
def main(dataset: str = "data/hotpot_mini.json", out_dir: str = "outputs/sample_run", reflexion_attempts: int = 3) -> None:
    examples = load_dataset(dataset)
    print(f"[cyan]Loaded {len(examples)} examples from {dataset}[/cyan]")

    react = ReActAgent()
    reflexion = ReflexionAgent(max_attempts=reflexion_attempts)

    react_records = []
    for example in track(examples, description="[green]ReAct   "):
        record = react.run(example)
        react_records.append(record)
        status = "✓" if record.is_correct else "✗"
        print(f"  {status} [{record.qid}] predicted={record.predicted_answer!r}  tokens={record.token_estimate}  latency={record.latency_ms}ms")

    reflexion_records = []
    for example in track(examples, description="[blue]Reflexion"):
        record = reflexion.run(example)
        reflexion_records.append(record)
        status = "✓" if record.is_correct else "✗"
        print(f"  {status} [{record.qid}] attempts={record.attempts}  predicted={record.predicted_answer!r}  tokens={record.token_estimate}  latency={record.latency_ms}ms")

    all_records = react_records + reflexion_records
    out_path = Path(out_dir)
    save_jsonl(out_path / "react_runs.jsonl", react_records)
    save_jsonl(out_path / "reflexion_runs.jsonl", reflexion_records)
    report = build_report(all_records, dataset_name=Path(dataset).name, mode="mock")
    json_path, md_path = save_report(report, out_path)
    print(f"\n[green]Saved[/green] {json_path}")
    print(f"[green]Saved[/green] {md_path}")
    print(json.dumps(report.summary, indent=2))

if __name__ == "__main__":
    app()


if __name__ == "__main__":
    app()

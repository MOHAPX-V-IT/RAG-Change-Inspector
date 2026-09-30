import argparse
import json
import sys
from pathlib import Path
from .core import compare, render, validate


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] not in (
        "compare",
        "validate",
        "init",
        "-h",
        "--help",
        "--version",
    ):
        argv.insert(0, "compare")
    parser = argparse.ArgumentParser(
        description="Find retrieval regressions before shipping."
    )
    parser.add_argument(
        "--version", action="version", version="RAG Change Inspector 0.2.0"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Create two runnable synthetic snapshots")
    init.add_argument("directory", type=Path, nargs="?", default=Path("rag-demo"))
    valid = sub.add_parser("validate", help="Validate a snapshot without comparing")
    valid.add_argument("snapshot", type=Path)
    run = sub.add_parser("compare", help="Compare snapshots and write optional reports")
    run.add_argument("before", type=Path)
    run.add_argument("after", type=Path)
    run.add_argument("--k", type=int, default=5)
    run.add_argument("--max-drop", type=float, default=0.0)
    run.add_argument(
        "--fail-on-question",
        action="store_true",
        help="Fail for any question beyond the drop threshold",
    )
    run.add_argument("--html", type=Path)
    run.add_argument("--json", dest="json_path", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            paths = [args.directory / "before.json", args.directory / "after.json"]
            if any(p.exists() for p in paths):
                raise ValueError(
                    "Demo snapshots already exist; choose another directory"
                )
            args.directory.mkdir(parents=True, exist_ok=True)
            for path, sources in zip(paths, [("policy", "other"), ("other", "policy")]):
                snapshot = {
                    "version": 1,
                    "questions": [
                        {
                            "id": "booking-policy",
                            "text": "How do I cancel a booking?",
                            "relevant_sources": ["policy"],
                            "results": [
                                {
                                    "source_id": s,
                                    "chunk_id": s + "-1",
                                    "text": "Cancel a booking before its start time."
                                    if s == "policy"
                                    else "Meeting room capacity and floor plan.",
                                }
                                for s in sources
                            ],
                        }
                    ],
                }
                with path.open("x", encoding="utf-8") as file:
                    json.dump(snapshot, file, indent=2)
            print(f"Created snapshots in {args.directory}")
            return 0
        if args.command == "validate":
            print(f"Valid: {len(validate(load(args.snapshot)))} questions")
            return 0
        report = compare(
            load(args.before),
            load(args.after),
            args.k,
            args.max_drop,
            args.fail_on_question,
        )
        outputs = [p.resolve() for p in (args.html, args.json_path) if p]
        if len(set(outputs)) != len(outputs):
            raise ValueError("Report paths must be different")
        if set(outputs) & {args.before.resolve(), args.after.resolve()}:
            raise ValueError("Reports cannot overwrite snapshots")
        for path, content in [
            (args.html, render(report)),
            (args.json_path, json.dumps(report, indent=2, ensure_ascii=False)),
        ]:
            if path:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
        print(f"Compared {report['evaluated']} labelled questions at k={args.k}")
        for metric, before in report["aggregate"]["before"].items():
            after = report["aggregate"]["after"][metric]
            print(
                f"{metric.upper():10} "
                + (
                    "N/A"
                    if before is None
                    else f"{before:.3f} -> {after:.3f} ({after - before:+.3f})"
                )
            )
        for key in ("missing_after", "new_after", "unlabelled"):
            if report[key]:
                print(f"{key}: {', '.join(report[key])}")
        if not report["evaluated"]:
            return 2
        return int(report["regression"] or bool(report["missing_after"]))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"Invalid input: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())

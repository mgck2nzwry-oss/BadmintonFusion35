from __future__ import annotations

from argparse import ArgumentParser
from hashlib import sha256
from pathlib import Path
import ast
import json
import re


def main() -> int:
    parser = ArgumentParser(description="Create a redacted, read-only inventory of legacy Python scripts")
    parser.add_argument("--root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(root)
    rows: list[dict[str, object]] = []
    for path in sorted(root.glob("*.py")):
        raw = path.read_bytes()
        text = raw.decode("utf-8-sig", errors="replace")
        parse_status = "PASS"
        try:
            tree = ast.parse(text, filename=path.name)
            functions = sum(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) for node in ast.walk(tree))
        except SyntaxError:
            parse_status = "FAIL"
            functions = 0
        rows.append(
            {
                "file": path.name,
                "size_bytes": len(raw),
                "line_count": text.count("\n") + 1,
                "sha256": sha256(raw).hexdigest().upper(),
                "syntax": parse_status,
                "function_count": functions,
                "has_main_guard": "if __name__" in text,
                "has_argparse": "argparse" in text,
                "local_path_reference_count": len(
                    re.findall(r"(?:[A-Z]:\\|Pose2SimProjects|USERPROFILE)", text, flags=re.IGNORECASE)
                ),
            }
        )
    report = {
        "status": "PASS" if all(row["syntax"] == "PASS" for row in rows) else "REVIEW",
        "root_redacted": "<LEGACY_PROJECT_ROOT>",
        "script_count": len(rows),
        "total_lines": sum(int(row["line_count"]) for row in rows),
        "main_guard_count": sum(bool(row["has_main_guard"]) for row in rows),
        "argparse_count": sum(bool(row["has_argparse"]) for row in rows),
        "local_path_reference_count": sum(int(row["local_path_reference_count"]) for row in rows),
        "scripts": rows,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "scripts"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

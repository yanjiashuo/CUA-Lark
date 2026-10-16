#!/usr/bin/env python3
from __future__ import annotations

import compileall
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(label: str, command: list[str]) -> None:
    print(f"[verify] {label}")
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    print("[verify] compile Python sources")
    if not compileall.compile_dir(ROOT / "cua_lark", quiet=1):
        raise SystemExit("Python compilation failed")
    if not compileall.compile_dir(ROOT / "scripts", quiet=1):
        raise SystemExit("Script compilation failed")

    run("project tests", [sys.executable, "-m", "pytest", "-q"])
    run("CLI help", [sys.executable, "scripts/run_test.py", "--help"])
    run("security scan", [sys.executable, "scripts/security_scan.py"])
    print("[verify] release verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IGNORED_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "results", "outputs"}
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".mov", ".mp4", ".pyc"}
MAX_PUBLIC_FILE_BYTES = 10 * 1024 * 1024

PATTERNS = {
    "provider_api_key": re.compile(rb"\b(?:sk|ark)-[A-Za-z0-9_-]{20,}\b"),
    "aws_access_key": re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    "github_token": re.compile(rb"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    "private_key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "personal_absolute_path": re.compile(rb"(?<![A-Za-z0-9])/(?:Users|home)/[^/\s]+/"),
}


def scan_bytes(data: bytes) -> set[str]:
    return {name for name, pattern in PATTERNS.items() if pattern.search(data)}


def iter_public_files():
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in IGNORED_DIRS or part.endswith(".egg-info") for part in path.parts):
            continue
        yield path


def scan_worktree() -> list[str]:
    findings: list[str] = []
    forbidden_names = {".env", "config.yaml"}
    forbidden_suffixes = {".zip", ".tar", ".tgz", ".mov", ".mp4"}
    for path in iter_public_files():
        rel = path.relative_to(ROOT)
        if path.name in forbidden_names:
            findings.append(f"forbidden local file: {rel}")
        if path.suffix.lower() in forbidden_suffixes:
            findings.append(f"forbidden archive/media: {rel}")
        size = path.stat().st_size
        if size > MAX_PUBLIC_FILE_BYTES:
            findings.append(f"oversized file ({size} bytes): {rel}")
        if path.suffix.lower() in BINARY_SUFFIXES:
            continue
        try:
            data = path.read_bytes()
        except OSError as exc:
            findings.append(f"unreadable file: {rel}: {exc}")
            continue
        for category in sorted(scan_bytes(data)):
            findings.append(f"{category}: {rel}")
    return findings


def scan_git_history() -> list[str]:
    if not (ROOT / ".git").exists():
        return ["git history scan skipped: repository is not initialized"]
    process = subprocess.run(
        ["git", "log", "-p", "--all", "--no-ext-diff", "--binary"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode != 0:
        return [f"git history scan failed: {process.stderr.decode(errors='replace').strip()}"]
    return [f"git_history_{name}" for name in sorted(scan_bytes(process.stdout))]


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan the CUA-Lark release for secrets and repository hygiene risks.")
    parser.add_argument("--git-history", action="store_true", help="Also scan every Git diff in local history")
    args = parser.parse_args()

    findings = scan_worktree()
    history_messages: list[str] = []
    if args.git_history:
        history_messages = scan_git_history()
        findings.extend(item for item in history_messages if "skipped" not in item)

    if findings:
        print("Security scan failed:")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print("Security scan passed: no credential, absolute-path, archive, or oversized-file findings.")
    for message in history_messages:
        print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

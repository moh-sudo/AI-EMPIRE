"""Weekly check for secrets accidentally committed to git.

Scans every file git currently tracks (working tree content, not full
history) for patterns that look like real API keys/tokens. Placeholder
values (REPLACE_ME, empty, "xxx", etc.) and .env.example are ignored.

Usage:
    python infrastructure/scripts/secret_scan.py

Exit code 0 = clean, 1 = findings, 2 = not a git repo / git not available.
Intended to run weekly via n8n or a scheduled task, per CONTEXT.md.
"""

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PLACEHOLDER_PATTERN = re.compile(r"REPLACE_ME|CHANGE_ME|<.*>|xxxx+|your[_-]?key", re.IGNORECASE)

SECRET_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("Anthropic API key", re.compile(r"sk-ant-[A-Za-z0-9\-_]{20,}")),
    ("OpenAI API key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("Resend API key", re.compile(r"re_[A-Za-z0-9]{20,}")),
    ("Supabase/JWT-style service key", re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("AWS access key ID", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("Generic private key block", re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("Generic secret assignment", re.compile(r"(?i)(secret|token|password|api_key)\s*[:=]\s*['\"][A-Za-z0-9+/=_\-]{16,}['\"]")),
]

IGNORED_FILES = {".env.example"}
IGNORED_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__"}


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print("secret_scan: not a git repository or git not available", file=sys.stderr)
        sys.exit(2)
    return [REPO_ROOT / line for line in result.stdout.splitlines() if line]


def scan_file(path: Path) -> list[tuple[int, str, str]]:
    if path.name in IGNORED_FILES:
        return []
    if any(part in IGNORED_DIRS for part in path.parts):
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []

    findings = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if PLACEHOLDER_PATTERN.search(line):
            continue
        for label, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                findings.append((line_no, label, line.strip()[:120]))
    return findings


def main() -> int:
    any_findings = False
    for path in tracked_files():
        for line_no, label, snippet in scan_file(path):
            any_findings = True
            rel = path.relative_to(REPO_ROOT)
            print(f"[SECRET?] {rel}:{line_no} — {label}: {snippet}")

    if any_findings:
        print("\nsecret_scan: potential secrets found in tracked files (see above).")
        return 1

    print("secret_scan: clean — no committed secrets detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

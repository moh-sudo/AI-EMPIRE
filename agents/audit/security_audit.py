"""Security Audit -- Audit & Verification Division.

Real checks against the actual repository, not simulated. Fully
deterministic -- no LLM needed for any of these, so nothing here is
stubbed for that reason.
"""

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Patterns that look like real hardcoded secrets, not just the word
# "key"/"token" in a comment or variable name. Deliberately narrow --
# false positives erode trust in the check faster than a missed one.
_SECRET_PATTERNS = [
    (re.compile(r'["\']sk-[A-Za-z0-9]{20,}["\']'), "OpenAI-style API key"),
    (re.compile(r'["\']tvly-[A-Za-z0-9_-]{20,}["\']'), "Tavily API key"),
    (re.compile(r'["\']AIza[A-Za-z0-9_-]{30,}["\']'), "Google API key"),
    (re.compile(r'["\']\d{9,10}:[A-Za-z0-9_-]{30,}["\']'), "Telegram bot token"),
    (re.compile(r'["\']GOCSPX-[A-Za-z0-9_-]{20,}["\']'), "Google OAuth client secret"),
]

# Files/dirs never worth scanning -- huge, third-party, or binary.
_SKIP_DIRS = {".venv", "__pycache__", ".git", "node_modules", ".downloads"}


def scan_for_hardcoded_secrets() -> dict:
    """Walks the real repo (excluding .venv/.git/etc.) looking for
    string literals that match known secret formats -- catches a
    secret accidentally pasted into code instead of .env. Never
    flags .env itself (secrets belong there)."""
    findings = []
    for py_file in REPO_ROOT.rglob("*.py"):
        if any(part in _SKIP_DIRS for part in py_file.parts):
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern, label in _SECRET_PATTERNS:
            for match in pattern.finditer(content):
                line_number = content[: match.start()].count("\n") + 1
                findings.append(
                    {
                        "file": str(py_file.relative_to(REPO_ROOT)),
                        "line": line_number,
                        "type": label,
                    }
                )
    return {"ok": True, "findings": findings}


def scan_git_history_for_secrets() -> dict:
    """Same patterns as scan_for_hardcoded_secrets(), applied to the
    full commit history via 'git log -p' instead of just the current
    working tree -- catches a secret that was later removed from the
    live code but still sits, retrievable, in an old commit (this is
    a real, common way secrets leak even after being "fixed": a
    working-tree scan looks clean, but `git log -p` or a clone still
    has it). Flagged as a real gap 2026-08-11, scoped and built
    2026-08-18. 90 commits in this repo as of scoping -- small enough
    that 'git log -p' runs in well under the timeout; --all wasn't
    used since this repo has no other branches to check.

    Only scans ADDED lines ('+' in the diff) -- that's where a secret
    would actually have been introduced; a '-' line just shows
    something that already existed being removed, already covered by
    whichever commit originally added it."""
    try:
        result = subprocess.run(
            ["git", "log", "-p", "--no-color"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
    except (subprocess.SubprocessError, OSError, UnicodeDecodeError) as e:
        return {"ok": False, "reason": str(e)}

    findings = []
    current_commit = None
    current_file = None
    for line in result.stdout.splitlines():
        if line.startswith("commit "):
            current_commit = line.split()[1]
            continue
        if line.startswith("+++ b/"):
            current_file = line[len("+++ b/") :]
            continue
        if line.startswith("+++ /dev/null"):
            current_file = None
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        if current_file == ".env":
            continue  # matches scan_for_hardcoded_secrets()'s own "never flags .env itself" rule

        content = line[1:]
        for pattern, label in _SECRET_PATTERNS:
            for _match in pattern.finditer(content):
                findings.append({"commit": current_commit, "file": current_file, "type": label})

    return {"ok": True, "findings": findings}


def check_env_not_tracked() -> dict:
    """Confirms .env is genuinely excluded from git, not just assumed
    via .gitignore's presence -- checks git's actual tracked-file list."""
    try:
        result = subprocess.run(
            ["git", "ls-files", ".env"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.SubprocessError, OSError) as e:
        return {"ok": False, "reason": str(e)}

    is_tracked = bool(result.stdout.strip())
    return {"ok": True, "env_tracked_by_git": is_tracked}


def check_dependency_vulnerabilities() -> dict:
    """Uses pip-audit if installed -- real CVE data against whatever's
    actually installed in this venv. Invoked as 'python -m pip_audit'
    (not the bare 'pip-audit' command) -- found live 2026-08-03 that
    the bare command isn't reliably on PATH for a subprocess even when
    the package is installed in this venv; module invocation always
    resolves correctly since it uses the same interpreter this code is
    running under. Deliberately auditing the environment directly
    rather than 'pip-audit -r requirements.txt' -- the latter makes
    pip-audit do a fresh dependency resolution from scratch (downloading
    and resolving the whole tree) which was observed live to still be
    running past 300 seconds; auditing already-installed packages just
    checks each installed version against the vulnerability DB and
    completes in well under a minute. Honest "not available" if the
    tool itself isn't installed, rather than silently skipping."""
    import sys

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip_audit", "--format", "json"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=240,
        )
    except FileNotFoundError:
        return {"ok": False, "reason": "pip-audit not installed -- run 'pip install pip-audit' to enable this check."}
    except subprocess.SubprocessError as e:
        return {"ok": False, "reason": str(e)}

    import json as json_module

    try:
        data = json_module.loads(result.stdout)
    except json_module.JSONDecodeError:
        return {"ok": False, "reason": f"pip-audit output could not be parsed: {result.stdout[:500]}"}

    vulnerable = [d for d in data.get("dependencies", []) if d.get("vulns")]
    return {"ok": True, "vulnerable_packages": vulnerable}


def run_security_audit() -> dict:
    """Live entry point -- runs all 4 real checks, isolated in their
    own try/except so one failing can't block the others."""
    results = {}

    try:
        results["secrets"] = scan_for_hardcoded_secrets()
    except Exception as e:
        results["secrets"] = {"ok": False, "reason": str(e)}

    try:
        results["git_history_secrets"] = scan_git_history_for_secrets()
    except Exception as e:
        results["git_history_secrets"] = {"ok": False, "reason": str(e)}

    try:
        results["env_tracking"] = check_env_not_tracked()
    except Exception as e:
        results["env_tracking"] = {"ok": False, "reason": str(e)}

    try:
        results["dependency_vulnerabilities"] = check_dependency_vulnerabilities()
    except Exception as e:
        results["dependency_vulnerabilities"] = {"ok": False, "reason": str(e)}

    return results

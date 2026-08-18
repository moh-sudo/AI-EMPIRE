from unittest.mock import MagicMock, patch

from agents.audit import security_audit as sa


def _git_log_result(stdout: str, returncode: int = 0):
    return MagicMock(returncode=returncode, stdout=stdout, stderr="")


def test_scan_git_history_for_secrets_finds_a_real_pattern_in_an_added_line():
    fake_log = (
        "commit abc123def456\n"
        "Author: Someone <someone@example.com>\n"
        "Date:   Mon Jan 1 00:00:00 2026\n"
        "\n"
        "    Add integration\n"
        "\n"
        "diff --git a/agents/forex/research.py b/agents/forex/research.py\n"
        "index 111..222 100644\n"
        "--- a/agents/forex/research.py\n"
        "+++ b/agents/forex/research.py\n"
        "@@ -1,3 +1,4 @@\n"
        '+key = "sk-xxxxxxxxxxxxxxxxxxxx"\n'
    )
    with patch.object(sa.subprocess, "run", return_value=_git_log_result(fake_log)):
        result = sa.scan_git_history_for_secrets()

    assert result["ok"] is True
    assert result["findings"] == [
        {"commit": "abc123def456", "file": "agents/forex/research.py", "type": "OpenAI-style API key"}
    ]


def test_scan_git_history_for_secrets_ignores_removed_lines():
    fake_log = (
        "commit abc123\n"
        "\n"
        "diff --git a/x.py b/x.py\n"
        "--- a/x.py\n"
        "+++ b/x.py\n"
        '-key = "sk-xxxxxxxxxxxxxxxxxxxx"\n'
        "+key = os.environ['OPENAI_API_KEY']\n"
    )
    with patch.object(sa.subprocess, "run", return_value=_git_log_result(fake_log)):
        result = sa.scan_git_history_for_secrets()

    assert result["findings"] == []


def test_scan_git_history_for_secrets_never_flags_env_file():
    fake_log = (
        "commit abc123\n"
        "\n"
        "diff --git a/.env b/.env\n"
        "--- /dev/null\n"
        "+++ b/.env\n"
        '+OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxxxxxx"\n'
    )
    with patch.object(sa.subprocess, "run", return_value=_git_log_result(fake_log)):
        result = sa.scan_git_history_for_secrets()

    assert result["findings"] == []


def test_scan_git_history_for_secrets_tracks_commit_and_file_across_multiple_commits():
    fake_log = (
        "commit commit1\n"
        "\n"
        "diff --git a/a.py b/a.py\n"
        "--- a/a.py\n"
        "+++ b/a.py\n"
        '+tavly_key = "tvly-xxxxxxxxxxxxxxxxxxxx"\n'
        "commit commit2\n"
        "\n"
        "diff --git a/b.py b/b.py\n"
        "--- a/b.py\n"
        "+++ b/b.py\n"
        '+google_key = "AIzaxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"\n'
    )
    with patch.object(sa.subprocess, "run", return_value=_git_log_result(fake_log)):
        result = sa.scan_git_history_for_secrets()

    commits_found = {f["commit"] for f in result["findings"]}
    assert commits_found == {"commit1", "commit2"}


def test_scan_git_history_for_secrets_fails_closed_on_subprocess_error():
    with patch.object(sa.subprocess, "run", side_effect=sa.subprocess.SubprocessError("boom")):
        result = sa.scan_git_history_for_secrets()
    assert result == {"ok": False, "reason": "boom"}


def test_run_security_audit_includes_git_history_secrets_key():
    with (
        patch.object(sa, "scan_for_hardcoded_secrets", return_value={"ok": True, "findings": []}),
        patch.object(sa, "scan_git_history_for_secrets", return_value={"ok": True, "findings": []}),
        patch.object(sa, "check_env_not_tracked", return_value={"ok": True, "env_tracked_by_git": False}),
        patch.object(sa, "check_dependency_vulnerabilities", return_value={"ok": True, "vulnerable_packages": []}),
    ):
        result = sa.run_security_audit()

    assert "git_history_secrets" in result
    assert result["git_history_secrets"]["ok"] is True


def test_run_security_audit_isolates_a_git_history_failure_from_other_checks():
    with (
        patch.object(sa, "scan_for_hardcoded_secrets", return_value={"ok": True, "findings": []}),
        patch.object(sa, "scan_git_history_for_secrets", side_effect=RuntimeError("boom")),
        patch.object(sa, "check_env_not_tracked", return_value={"ok": True, "env_tracked_by_git": False}),
        patch.object(sa, "check_dependency_vulnerabilities", return_value={"ok": True, "vulnerable_packages": []}),
    ):
        result = sa.run_security_audit()

    assert result["git_history_secrets"] == {"ok": False, "reason": "boom"}
    assert result["secrets"]["ok"] is True

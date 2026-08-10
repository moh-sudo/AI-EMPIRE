import json
from unittest.mock import patch

from agents.systems import workflow_builder as wb


def test_validate_parsed_accepts_a_valid_interval_workflow():
    parsed = {
        "division": "fixera",
        "name": "fixera-nightly-report",
        "trigger_type": "interval",
        "trigger_value": "1800",
        "endpoint": "/run-report",
    }
    assert wb._validate_parsed(parsed) is None


def test_validate_parsed_accepts_a_valid_cron_workflow():
    parsed = {
        "division": "systems",
        "name": "systems-nightly-cleanup",
        "trigger_type": "cron",
        "trigger_value": "0 3 * * *",
        "endpoint": "/cleanup",
    }
    assert wb._validate_parsed(parsed) is None


def test_validate_parsed_rejects_unknown_division():
    parsed = {"division": "marketing", "name": "x", "trigger_type": "interval", "trigger_value": "30", "endpoint": "/x"}
    assert "Unknown division" in wb._validate_parsed(parsed)


def test_validate_parsed_rejects_bad_kebab_case_name():
    parsed = {
        "division": "rii",
        "name": "Not Kebab Case",
        "trigger_type": "interval",
        "trigger_value": "30",
        "endpoint": "/x",
    }
    assert "kebab-case" in wb._validate_parsed(parsed)


def test_validate_parsed_rejects_non_numeric_interval():
    parsed = {"division": "rii", "name": "x", "trigger_type": "interval", "trigger_value": "soon", "endpoint": "/x"}
    assert "whole number of seconds" in wb._validate_parsed(parsed)


def test_validate_parsed_rejects_malformed_cron():
    parsed = {"division": "rii", "name": "x", "trigger_type": "cron", "trigger_value": "not a cron", "endpoint": "/x"}
    assert "cron expression" in wb._validate_parsed(parsed)


def test_validate_parsed_rejects_endpoint_without_leading_slash():
    parsed = {"division": "rii", "name": "x", "trigger_type": "interval", "trigger_value": "30", "endpoint": "x"}
    assert "must start with /" in wb._validate_parsed(parsed)


def test_build_workflow_json_interval_matches_existing_schema_shape():
    parsed = {
        "division": "rii",
        "name": "rii-test-poll",
        "trigger_type": "interval",
        "trigger_value": "30",
        "endpoint": "/check-telegram",
    }
    workflow = wb._build_workflow_json(parsed)

    assert workflow["name"] == "rii-test-poll"
    assert len(workflow["nodes"]) == 2
    trigger, http = workflow["nodes"]
    assert trigger["type"] == "n8n-nodes-base.scheduleTrigger"
    assert trigger["parameters"]["rule"]["interval"][0] == {"field": "seconds", "secondsInterval": 30}
    assert http["type"] == "n8n-nodes-base.httpRequest"
    assert http["parameters"]["url"] == "http://127.0.0.1:8006/check-telegram"
    assert http["parameters"]["method"] == "POST"
    assert workflow["connections"][trigger["name"]]["main"][0][0]["node"] == http["name"]
    assert workflow["active"] is True
    assert workflow["meta"]["instanceId"] == wb._INSTANCE_ID


def test_build_workflow_json_cron_uses_cron_expression_field():
    parsed = {
        "division": "systems",
        "name": "systems-nightly-cleanup",
        "trigger_type": "cron",
        "trigger_value": "0 3 * * *",
        "endpoint": "/cleanup",
    }
    workflow = wb._build_workflow_json(parsed)
    trigger = workflow["nodes"][0]
    assert trigger["parameters"]["rule"]["interval"][0] == {"field": "cronExpression", "expression": "0 3 * * *"}
    assert workflow["nodes"][1]["parameters"]["url"] == "http://127.0.0.1:8007/cleanup"


def test_parse_description_returns_structured_fields_on_a_clean_reply():
    reply = (
        "DIVISION: fixera\n"
        "NAME: fixera-nightly-report\n"
        "TRIGGER_TYPE: interval\n"
        "TRIGGER_VALUE: 1800\n"
        "ENDPOINT: /run-report"
    )
    with patch("shared.models.generate.chat", return_value={"ok": True, "reply": reply}):
        parsed = wb._parse_description("every 30 minutes, tell fixera to run its report")

    assert parsed == {
        "ok": True,
        "division": "fixera",
        "name": "fixera-nightly-report",
        "trigger_type": "interval",
        "trigger_value": "1800",
        "endpoint": "/run-report",
    }


def test_parse_description_reports_missing_fields_instead_of_raising():
    with patch("shared.models.generate.chat", return_value={"ok": True, "reply": "DIVISION: fixera"}):
        parsed = wb._parse_description("something vague")
    assert parsed["ok"] is False
    assert "missing fields" in parsed["reason"]


def test_parse_description_propagates_a_chat_failure():
    with patch("shared.models.generate.chat", return_value={"ok": False, "reason": "Ollama unreachable"}):
        parsed = wb._parse_description("anything")
    assert parsed == {"ok": False, "reason": "Ollama unreachable"}


def test_build_workflow_writes_a_new_file(tmp_path):
    reply = "DIVISION: rii\nNAME: rii-test-poll\nTRIGGER_TYPE: interval\nTRIGGER_VALUE: 30\nENDPOINT: /check-telegram"
    with (
        patch("shared.models.generate.chat", return_value={"ok": True, "reply": reply}),
        patch.object(wb, "WORKFLOWS_DIR", tmp_path),
    ):
        result = wb.build_workflow("check rii telegram every 30 seconds")

    assert result["ok"] is True
    written = tmp_path / "rii-test-poll.json"
    assert written.exists()
    assert json.loads(written.read_text())["name"] == "rii-test-poll"


def test_build_workflow_refuses_to_overwrite_an_existing_file(tmp_path):
    (tmp_path / "rii-test-poll.json").write_text("{}")
    reply = "DIVISION: rii\nNAME: rii-test-poll\nTRIGGER_TYPE: interval\nTRIGGER_VALUE: 30\nENDPOINT: /check-telegram"
    with (
        patch("shared.models.generate.chat", return_value={"ok": True, "reply": reply}),
        patch.object(wb, "WORKFLOWS_DIR", tmp_path),
    ):
        result = wb.build_workflow("check rii telegram every 30 seconds")

    assert result["ok"] is False
    assert "already exists" in result["reason"]


def test_build_workflow_fails_closed_on_invalid_division(tmp_path):
    reply = "DIVISION: marketing\nNAME: x\nTRIGGER_TYPE: interval\nTRIGGER_VALUE: 30\nENDPOINT: /x"
    with (
        patch("shared.models.generate.chat", return_value={"ok": True, "reply": reply}),
        patch.object(wb, "WORKFLOWS_DIR", tmp_path),
    ):
        result = wb.build_workflow("check marketing every 30 seconds")

    assert result["ok"] is False
    assert result["stage"] == "validate"
    assert not list(tmp_path.iterdir())

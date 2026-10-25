from back.llm.base import parse_json_response


def test_parse_json_with_code_fence() -> None:
    assert parse_json_response('```json\n{"a": 1}\n```') == {"a": 1}


def test_parse_json_with_noise() -> None:
    assert parse_json_response('text {"a": 2} tail') == {"a": 2}


def test_pending_report_marks_analysis_as_pending() -> None:
    from back.services.agent import pending_report

    report = pending_report({"agent_steps": [], "analysis_finished_at": "24.10 12:00"})

    assert report["analysis_pending"] is True
    assert "analysis_finished_at" not in report
    assert report["agent_steps"]

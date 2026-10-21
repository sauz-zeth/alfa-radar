from back.llm.base import parse_json_response


def test_parse_json_with_code_fence() -> None:
    assert parse_json_response('```json\n{"a": 1}\n```') == {"a": 1}


def test_parse_json_with_noise() -> None:
    assert parse_json_response('text {"a": 2} tail') == {"a": 2}

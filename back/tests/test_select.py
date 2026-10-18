from back.pipeline.select import Candidate, select_for_llm


def test_mentions_go_before_prescore_candidates() -> None:
    candidates = [
        Candidate(event_id=1, prescore=0.9, has_mention=False),
        Candidate(event_id=2, prescore=0.1, has_mention=True),
    ]
    selected = select_for_llm(candidates, tau=0.5, limit=2)
    assert [item.event_id for item in selected] == [2, 1]


def test_low_prescore_without_mention_is_dropped() -> None:
    candidates = [Candidate(event_id=1, prescore=0.4, has_mention=False)]
    assert select_for_llm(candidates, tau=0.5, limit=20) == []


def test_hourly_limit_is_enforced() -> None:
    candidates = [
        Candidate(event_id=index, prescore=1.0 - index / 100, has_mention=True)
        for index in range(10)
    ]
    assert len(select_for_llm(candidates, tau=0.5, limit=3)) == 3

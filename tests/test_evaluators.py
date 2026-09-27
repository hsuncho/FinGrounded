"""evaluators 순수 함수 단위 테스트"""
from evals import evaluators as ev


def test_extract_numbers_handles_commas_and_percent():
    nums = ev.extract_numbers("영업이익률은 2.54%이고 매출은 258,935,494백만원입니다")
    assert 2.54 in nums
    assert 258935494.0 in nums


def test_numeric_match_within_tolerance():
    ans = "삼성전자의 2023년 부채비율은 25.36%입니다."
    assert ev.numeric_match(ans, 25.36, tol=0.5)
    assert ev.numeric_match(ans, 25.0, tol=0.5)      # 오차 이내
    assert not ev.numeric_match(ans, 30.0, tol=0.5)  # 오차 밖


def test_numeric_match_ignores_amount_noise():
    # 거대한 금액이나 다른 회사 값이 비율 기대값과 오인 매칭되면 안 된다
    ans = "2023년 부채비율은 25.36%이며 부채총계는 92,228,115백만원입니다."
    assert ev.numeric_match(ans, 25.36, tol=0.5)       # 정답 비율은 매칭
    assert not ev.numeric_match(ans, 87.52, tol=0.5)   # 다른 회사 값은 매칭 안 됨
    assert not ev.numeric_match(ans, 40.0, tol=0.5)    # 존재하지 않는 값


def test_is_refusal_true_when_no_sources_and_marker():
    assert ev.is_refusal("해당 연도의 데이터를 찾을 수 없습니다.", [])


def test_is_refusal_false_when_sources_present():
    assert not ev.is_refusal("부채비율은 25.36%입니다.", [{"title": "x"}])


def test_has_grounding():
    assert ev.has_grounding("답", [{"title": "x"}])
    assert not ev.has_grounding("답", [])


def test_contains_all():
    ans = "1. SK하이닉스: 87.52%\n2. 삼성전자: 25.36%"
    assert ev.contains_all(ans, ["삼성전자", "SK하이닉스"])
    assert not ev.contains_all(ans, ["삼성전자", "카카오"])

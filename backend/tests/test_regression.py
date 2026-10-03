"""회귀 게이트: 골든셋 평가 지표가 임계값 아래로 떨어지면 실패시킨다."""
import os

import pytest

# 임계값(회귀 기준) — 데이터·모델 개선에 따라 상향 조정
THRESHOLDS = {
    "tool_selection": 0.90,
    "numeric": 0.90,
    "refusal": 1.00,
    "comparison": 0.90,
    "grounding": 0.90,
    "retrieval_hit": 0.80,
    "overall_pass_rate": 0.85,
}


@pytest.fixture(scope="module")
def report():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY 없음 → 통합 회귀 테스트 skip")
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL 없음 → 통합 회귀 테스트 skip")
    from evals.run_eval import main
    return main()


@pytest.mark.parametrize("metric,threshold", list(THRESHOLDS.items()))
def test_metric_above_threshold(report, metric, threshold):
    value = report["metrics"].get(metric)
    assert value is not None, f"지표 {metric} 가 리포트에 없음"
    assert value >= threshold, f"{metric}={value} < 임계값 {threshold} (회귀)"

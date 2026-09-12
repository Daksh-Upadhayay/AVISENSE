import numpy as np
import pytest

from app.ml.cmapss import DATASETS, load_test
from app.ml.features import build_features


@pytest.fixture(scope="module")
def engine():
    df = load_test("FD004")
    return df[df["unit"] == 1].reset_index(drop=True)


def test_features_only_use_the_past(model, engine):
    """Features at cycle t must not change when later cycles are added."""
    full = build_features(engine, model.normalizer)
    k = len(engine) // 2
    half = build_features(engine.iloc[:k], model.normalizer)
    np.testing.assert_allclose(full.iloc[:k].to_numpy(), half.to_numpy())


def test_assessment_is_internally_consistent(model, engine):
    a = model.assess(engine)
    assert a["rul_low"] <= a["rul"] <= a["rul_high"]
    assert 0 <= a["failure_probability"] <= 1
    assert a["status"] in {"healthy", "watch", "critical"}
    assert len(a["trajectory"]) == len(engine)
    # SHAP contributions add up to the raw model output.
    e = a["explanation"]
    total = e["base_rul"] + sum(c["cycles"] for c in e["contributions"])
    assert total == pytest.approx(e["raw_rul"], abs=0.5)
    assert a["rul"] == pytest.approx(min(max(e["raw_rul"], 0), model.policy.rul_cap), abs=0.2)


def test_row_order_does_not_matter(model, engine):
    a = model.assess(engine)
    b = model.assess(engine.sample(frac=1, random_state=0))
    assert a["rul"] == b["rul"]


def test_status_follows_the_published_policy(model):
    p = model.policy
    assert model.status(rul_low=100, failure_probability=p.alert_threshold) == "critical"
    assert model.status(rul_low=p.watch_rul, failure_probability=0.0) == "watch"
    assert model.status(rul_low=p.watch_rul + 1, failure_probability=0.0) == "healthy"


def test_near_failure_engines_are_flagged(model):
    df = load_test("FD001")
    last = df.groupby("unit")["rul"].last()
    for unit in last[last <= 10].index[:5]:
        a = model.assess(df[df["unit"] == unit])
        assert a["status"] == "critical", unit
        assert a["rul"] < 30


def test_bad_history_is_rejected(model, engine):
    with pytest.raises(ValueError, match="Missing columns"):
        model.assess(engine.drop(columns=["sensor_11"]))
    with pytest.raises(ValueError, match="Duplicate"):
        model.assess(engine.iloc[[0, 0, 1]])


def test_published_metrics_meet_the_release_bar(model):
    """Guards against a retrain silently shipping a worse model."""
    metrics = model.meta["metrics"]
    for name in DATASETS:
        m = metrics["per_dataset"][name]
        assert m["rmse"] < 12.5, name
        assert m["pr_auc"] > 0.9, name
        assert 0.7 < m["interval_coverage"] < 0.95, name
    assert metrics["overall"]["recall"] > 0.85

"""Pruebas del backend. Ejecutar:  pytest -q"""
import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import app  # noqa: E402
from backend import cleaning, data_io, diagnostics, regression  # noqa: E402


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


def make_data(n=150, seed=1):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, 3))
    y = 2 + 1.5 * X[:, 0] - 0.8 * X[:, 1] + 0.3 * X[:, 2] + rng.normal(0, 1, n)
    return X, y


def test_ols_matches_closed_form():
    X, y = make_data()
    res = regression.fit_ols(X, y, ["a", "b", "c"])
    A = np.column_stack([np.ones(len(y)), X])
    beta = np.linalg.solve(A.T @ A, A.T @ y)
    np.testing.assert_allclose(res.beta, beta, rtol=1e-9)
    # p-valor del intercepto con scipy
    assert res.p[0] == pytest.approx(2 * stats.t.sf(abs(res.t[0]), res.df_resid))
    assert 0.5 < res.r2 < 1 and res.r2_adj < res.r2


def test_simple_regression_equals_scipy():
    X, y = make_data()
    res = regression.fit_ols(X[:, :1], y, ["a"])
    lr = stats.linregress(X[:, 0], y)
    assert res.beta[1] == pytest.approx(lr.slope)
    assert res.p[1] == pytest.approx(lr.pvalue)
    assert res.r2 == pytest.approx(lr.rvalue ** 2)


def test_perfect_collinearity_raises():
    X, y = make_data()
    X2 = np.column_stack([X, X[:, 0] * 2])
    with pytest.raises(ValueError):
        regression.fit_ols(X2, y, list("abcd"))


def test_diagnostics_on_clean_data():
    X, y = make_data(300)
    res = regression.fit_ols(X, y, list("abc"))
    t = diagnostics.run_tests(res)
    assert all(n["passed"] for n in t["normality"])
    assert 1.5 < t["autocorrelation"]["statistic"] < 2.5
    assert all(h["p_value"] > 0.01 for h in t["homoscedasticity"])
    assert all(not v["high"] for v in t["vif"])


def test_heteroscedasticity_and_vif_detected():
    rng = np.random.default_rng(3)
    n = 400
    x1 = rng.uniform(1, 10, n)
    x2 = x1 * 3 + rng.normal(0, 0.05, n)           # casi colineal
    y = 1 + 2 * x1 + rng.normal(0, 1, n) * x1       # varianza crece con x1
    res = regression.fit_ols(np.column_stack([x1, x2]), y, ["x1", "x2"])
    t = diagnostics.run_tests(res)
    assert any(h["key"] == "bp" and not h["passed"] for h in t["homoscedasticity"])
    assert all(v["high"] for v in t["vif"])


def test_delimiter_detection():
    assert data_io.detect_delimiter("a;b;c\n1;2;3\n4;5;6") == ";"
    assert data_io.detect_delimiter("a\tb\n1\t2\n3\t4") == "\t"
    assert data_io.detect_delimiter("a,b,c\n1,2,3") == ","


def test_name_validation():
    names, changes = data_io.validate_names(["Precio ($)", "área m2", "área m2", "2020"])
    assert len(set(names)) == 4 and all(n.isidentifier() for n in names)
    assert changes


def test_cleaning_strategies():
    df = pd.DataFrame({"a": [1, 2, 3, 4, 5, 100.0, np.nan], "b": [1, 2, 3, 4, 5, 6, 7.0]})
    mean, _ = cleaning.clean(df, missing="mean")
    assert not mean.isna().any().any()
    dropped, _ = cleaning.clean(df, missing="drop")
    assert len(dropped) == 6
    removed, _ = cleaning.clean(df, missing="drop", outliers="remove")
    assert 100.0 not in removed["a"].values
    capped, _ = cleaning.clean(df, missing="drop", outliers="cap")
    assert capped["a"].max() < 100


def test_describe_quartiles():
    d = cleaning.describe(pd.DataFrame({"x": [1, 2, 3, 4, 5.0]}))[0]
    assert d["mean"] == 3 and d["variance"] == 2.5 and d["q1"] == 2 and d["q3"] == 4


def test_end_to_end_api(client):
    r = client.get("/api/sample")
    assert r.status_code == 200
    d = r.get_json()
    token = d["token"]
    assert d["cols"] >= 6 and len(d["numeric"]) >= 6

    r = client.post("/api/clean", json={"token": token, "missing": "median", "outliers": "cap", "method": "iqr"})
    assert r.status_code == 200 and r.get_json()["log"]

    xs = [c for c in d["numeric"] if c != "precio_miles"]
    r = client.post("/api/fit", json={"token": token, "y": "precio_miles", "x": xs})
    fit = r.get_json()
    assert r.status_code == 200 and len(fit["coefficients"]) == len(xs) + 1
    assert fit["r2"] > 0.7

    r = client.post("/api/tests", json={"token": token})
    t = r.get_json()
    assert {"normality", "autocorrelation", "homoscedasticity", "vif"} <= set(t)
    assert any(v["high"] for v in t["vif"])     # area_m2 vs area_pies2

    r = client.post("/api/plots", json={"token": token})
    p = r.get_json()
    assert len(p["scatter"]) == len(xs) and len(p["qq"]["sample"]) == fit["n"]


def test_upload_semicolon_and_errors(client):
    csv = "ventas;publicidad;precio\n1,5;2;3\n2,5;3;4\n3,5;5;4\n5,0;7;6\n6,5;8;7\n"
    r = client.post("/api/upload", data={"file": (io.BytesIO(csv.encode()), "x.csv")},
                    content_type="multipart/form-data")
    d = r.get_json()
    assert r.status_code == 200 and d["delimiter"].startswith("punto y coma")
    assert "ventas" in d["numeric"]                 # coma decimal convertida
    bad = client.post("/api/fit", json={"token": d["token"], "y": "ventas", "x": []})
    assert bad.status_code == 400
    assert client.post("/api/tests", json={"token": "nope"}).status_code == 404

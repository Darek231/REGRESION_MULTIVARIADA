"""Módulo 4 · Validación del modelo.

4.1 Normalidad de residuos  : Shapiro-Wilk, Kolmogorov-Smirnov, Jarque-Bera
4.2 Autocorrelación         : Durbin-Watson
4.3 Homocedasticidad        : Breusch-Pagan, White
4.4 Multicolinealidad       : VIF  (VIFi = 1 / (1 - R²i))
"""
from __future__ import annotations

from itertools import combinations_with_replacement

import numpy as np
from scipy import stats

from .regression import OLSResult

ALPHA = 0.05


def _r2(A: np.ndarray, y: np.ndarray) -> tuple[float, int]:
    """R² y rango de una regresión auxiliar (A debe incluir el intercepto)."""
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    res = y - A @ beta
    sst = ((y - y.mean()) ** 2).sum()
    r2 = 0.0 if sst == 0 else 1 - float(res @ res) / sst
    return max(0.0, min(1.0, r2)), int(np.linalg.matrix_rank(A))


# ---------------------------------------------------------------- 4.1 Normalidad
def normality(resid: np.ndarray, method: str) -> dict:
    n = len(resid)
    if method == "shapiro":
        if n < 3:
            raise ValueError("Shapiro-Wilk requiere al menos 3 observaciones.")
        stat, p = stats.shapiro(resid)
        name = "Shapiro-Wilk"
        note = "W cercano a 1 indica normalidad." + (" (n > 5000: el p-valor es aproximado)" if n > 5000 else "")
    elif method == "ks":
        z = (resid - resid.mean()) / resid.std(ddof=1)
        stat, p = stats.kstest(z, "norm")
        name = "Kolmogorov-Smirnov"
        note = "Residuos estandarizados vs N(0,1). Con parámetros estimados es algo conservador."
    elif method == "jb":
        res = stats.jarque_bera(resid)
        stat, p = res[0], res[1]
        name = "Jarque-Bera"
        note = "Contrasta asimetría y curtosis frente a una normal."
    else:
        raise ValueError("Prueba de normalidad desconocida.")
    ok = bool(p >= ALPHA)
    return {
        "key": method, "name": name, "statistic": float(stat), "p_value": float(p), "passed": ok,
        "h0": "Los residuos siguen una distribución normal.",
        "conclusion": ("No se rechaza H0: no hay evidencia contra la normalidad de los residuos."
                       if ok else "Se rechaza H0: los residuos se desvían de la normalidad."),
        "note": note,
    }


# ---------------------------------------------------------------- 4.2 Autocorrelación
def durbin_watson(resid: np.ndarray) -> dict:
    d = float(np.sum(np.diff(resid) ** 2) / np.sum(resid ** 2))
    rho = 1 - d / 2
    if d < 1.5:
        concl, passed = "Evidencia de autocorrelación POSITIVA (d bien por debajo de 2).", False
    elif d > 2.5:
        concl, passed = "Evidencia de autocorrelación NEGATIVA (d bien por encima de 2).", False
    else:
        concl, passed = "No hay evidencia de autocorrelación (d ≈ 2).", True
    return {
        "key": "dw", "name": "Durbin-Watson", "statistic": d, "p_value": None, "passed": passed,
        "h0": "No existe autocorrelación de primer orden en los residuos.",
        "conclusion": concl,
        "note": f"Regla práctica: d<1.5 positiva · 1.5–2.5 sin autocorrelación · d>2.5 negativa. ρ̂ ≈ {rho:.3f}. "
                "Requiere datos ordenados (p. ej. en el tiempo).",
        "extra": {"rho": float(rho)},
    }


# ---------------------------------------------------------------- 4.3 Homocedasticidad
def _lm_test(res: OLSResult, Z: np.ndarray, name: str, key: str, note: str) -> dict:
    e2 = res.resid ** 2
    r2, rank = _r2(Z, e2)
    df = rank - 1
    if df < 1 or res.n <= rank:
        raise ValueError(f"No hay observaciones suficientes para la prueba {name}.")
    lm = res.n * r2
    p = float(stats.chi2.sf(lm, df))
    f = (r2 / df) / ((1 - r2) / (res.n - rank)) if r2 < 1 else float("inf")
    ok = bool(p >= ALPHA)
    return {
        "key": key, "name": name, "statistic": float(lm), "p_value": p, "passed": ok,
        "h0": "La varianza de los errores es constante (homocedasticidad).",
        "conclusion": ("No se rechaza H0: no hay evidencia de heterocedasticidad."
                       if ok else "Se rechaza H0: hay heterocedasticidad (varianza no constante)."),
        "note": note,
        "extra": {"df": int(df), "f_stat": float(f), "r2_aux": float(r2)},
    }


def breusch_pagan(res: OLSResult) -> dict:
    return _lm_test(res, res.A, "Breusch-Pagan", "bp",
                    "LM = n·R² de la regresión auxiliar e² ~ X (versión de Koenker, robusta a no normalidad).")


def white(res: OLSResult) -> dict:
    X = res.A[:, 1:]
    cols = [np.ones(res.n)] + [X[:, i] for i in range(X.shape[1])]
    for i, j in combinations_with_replacement(range(X.shape[1]), 2):
        cols.append(X[:, i] * X[:, j])
    Z = np.column_stack(cols)
    return _lm_test(res, Z, "White", "white",
                    "Regresión auxiliar e² ~ X, X² y productos cruzados (columnas redundantes se descartan por rango).")


# ---------------------------------------------------------------- 4.4 Multicolinealidad
def vif(res: OLSResult) -> list[dict]:
    X = res.A[:, 1:]
    k = X.shape[1]
    out = []
    for j in range(k):
        if k == 1:
            v, r2 = 1.0, 0.0
        else:
            others = np.delete(X, j, axis=1)
            r2, _ = _r2(np.column_stack([np.ones(res.n), others]), X[:, j])
            v = float("inf") if r2 >= 1 - 1e-12 else 1.0 / (1.0 - r2)
        out.append({"name": res.names[j + 1], "r2": float(r2), "vif": v, "high": bool(v > 10),
                    "level": "alto" if v > 10 else ("moderado" if v > 5 else "bajo")})
    return out


# ---------------------------------------------------------------- Orquestador
def run_tests(res: OLSResult, normality_sel: str = "all", hetero_sel: str = "all") -> dict:
    norm_keys = ["shapiro", "ks", "jb"] if normality_sel == "all" else [normality_sel]
    het_keys = ["bp", "white"] if hetero_sel == "all" else [hetero_sel]
    tests = {
        "normality": [normality(res.resid, k) for k in norm_keys],
        "autocorrelation": durbin_watson(res.resid),
        "homoscedasticity": [(breusch_pagan if k == "bp" else white)(res) for k in het_keys],
        "vif": vif(res),
        "alpha": ALPHA,
    }
    return tests

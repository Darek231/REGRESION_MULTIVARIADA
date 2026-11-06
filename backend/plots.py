"""Módulo 5 · Datos para los gráficos (el dibujo se hace en el navegador con <canvas>).

5.1 Dispersión Xi vs Y  ·  5.2 Histograma de residuos  ·  5.3 Q-Q  ·  5.4 Residuos estándar vs ajustados
"""
from __future__ import annotations

import numpy as np
from scipy import stats

from .regression import OLSResult


def build_plots(res: OLSResult) -> dict:
    X = res.A[:, 1:]
    y = res.y

    scatter = []
    for j, name in enumerate(res.names[1:]):
        x = X[:, j]
        if np.ptp(x) == 0:
            slope, intercept, r = 0.0, float(y.mean()), 0.0
        else:
            slope, intercept, r, *_ = stats.linregress(x, y)
        scatter.append({"name": name, "x": x, "y": y, "slope": float(slope),
                        "intercept": float(intercept), "r": float(r)})

    counts, edges = np.histogram(res.resid, bins="auto")
    if len(counts) > 40:
        counts, edges = np.histogram(res.resid, bins=40)
    hist = {"counts": counts, "edges": edges, "mean": float(res.resid.mean()),
            "std": float(res.resid.std(ddof=1)), "n": res.n}

    order = np.argsort(res.std_resid)
    n = res.n
    theo = stats.norm.ppf((np.arange(1, n + 1) - 0.375) / (n + 0.25))
    qq = {"theoretical": theo, "sample": res.std_resid[order]}

    rvf = {"fitted": res.fitted, "std_resid": res.std_resid}

    return {"scatter": scatter, "histogram": hist, "qq": qq, "resid_vs_fitted": rvf}

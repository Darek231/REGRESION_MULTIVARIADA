"""Módulo 3 · Estimación OLS (mínimos cuadrados ordinarios) implementada con NumPy.

    Y = β0 + β1·X1 + β2·X2 + ... + βk·Xk + ε
    β̂ = (AᵀA)⁻¹ Aᵀ y        (A = [1 | X])
    SE(β̂j) = sqrt( σ̂² · [(AᵀA)⁻¹]jj )      t = β̂j / SE      p = 2·P(T > |t|)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats


@dataclass
class OLSResult:
    names: list[str]            # ["Intercepto", x1, x2, ...]
    A: np.ndarray               # matriz de diseño con columna de 1s
    y: np.ndarray
    beta: np.ndarray
    se: np.ndarray
    t: np.ndarray
    p: np.ndarray
    ci_low: np.ndarray
    ci_high: np.ndarray
    fitted: np.ndarray
    resid: np.ndarray
    std_resid: np.ndarray       # residuos internamente estandarizados e / (s·√(1-h))
    leverage: np.ndarray
    n: int
    k: int                      # nº de regresores (sin intercepto)
    df_resid: int
    sigma: float
    sse: float
    sst: float
    r2: float
    r2_adj: float
    f_stat: float
    f_p: float
    aic: float
    bic: float

    def summary(self) -> dict:
        coefs = []
        for i, name in enumerate(self.names):
            coefs.append({
                "name": name,
                "beta": self.beta[i], "se": self.se[i], "t": self.t[i], "p": self.p[i],
                "ci_low": self.ci_low[i], "ci_high": self.ci_high[i],
            })
        return {
            "n": self.n, "k": self.k, "df_resid": self.df_resid,
            "sigma": self.sigma, "sse": self.sse, "sst": self.sst,
            "r2": self.r2, "r2_adj": self.r2_adj,
            "f_stat": self.f_stat, "f_p": self.f_p,
            "aic": self.aic, "bic": self.bic,
            "coefficients": coefs,
        }


def fit_ols(X: np.ndarray, y: np.ndarray, x_names: list[str]) -> OLSResult:
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    n, k = X.shape
    p = k + 1
    if n <= p:
        raise ValueError(f"Se necesitan más observaciones ({n}) que parámetros ({p}).")

    A = np.column_stack([np.ones(n), X])
    if np.linalg.matrix_rank(A) < p:
        raise ValueError("Multicolinealidad perfecta: hay variables que son combinación lineal de otras "
                         "(o constantes). Quita alguna variable independiente.")

    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    xtx_inv = np.linalg.inv(A.T @ A)
    fitted = A @ beta
    resid = y - fitted
    df_resid = n - p
    sse = float(resid @ resid)
    sst = float(((y - y.mean()) ** 2).sum())
    if sst == 0:
        raise ValueError("La variable dependiente es constante.")
    sigma2 = sse / df_resid
    if sigma2 == 0:
        raise ValueError("Ajuste perfecto (residuos nulos): no se pueden calcular errores estándar.")

    se = np.sqrt(np.diag(xtx_inv) * sigma2)
    t = beta / se
    pval = 2 * stats.t.sf(np.abs(t), df_resid)
    tcrit = stats.t.ppf(0.975, df_resid)

    r2 = 1 - sse / sst
    r2_adj = 1 - (1 - r2) * (n - 1) / df_resid
    f_stat = ((sst - sse) / k) / sigma2
    f_p = float(stats.f.sf(f_stat, k, df_resid))

    h = np.einsum("ij,jk,ik->i", A, xtx_inv, A)
    denom = np.sqrt(sigma2 * np.clip(1 - h, 1e-12, None))
    std_resid = resid / denom

    loglik = -0.5 * n * (np.log(2 * np.pi) + np.log(sse / n) + 1)
    aic = 2 * p - 2 * loglik
    bic = p * np.log(n) - 2 * loglik

    return OLSResult(
        names=["Intercepto"] + list(x_names), A=A, y=y, beta=beta, se=se, t=t, p=pval,
        ci_low=beta - tcrit * se, ci_high=beta + tcrit * se,
        fitted=fitted, resid=resid, std_resid=std_resid, leverage=h,
        n=n, k=k, df_resid=df_resid, sigma=float(np.sqrt(sigma2)), sse=sse, sst=sst,
        r2=float(r2), r2_adj=float(r2_adj), f_stat=float(f_stat), f_p=f_p,
        aic=float(aic), bic=float(bic),
    )

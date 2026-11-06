"""Módulo 2 · Limpieza y estadísticas descriptivas.

- Conversión de tipos.
- Valores faltantes: mantener / eliminar filas / imputar media o mediana.
- Valores atípicos: detección (IQR o Z-score) y tratamiento (eliminar / limitar).
- Estadísticas descriptivas: media, varianza, mínimo, máximo y cuartiles.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .data_io import to_numeric_series


def numeric_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]


def convert_types(df: pd.DataFrame, types: dict[str, str]) -> pd.DataFrame:
    out = df.copy()
    for col, kind in (types or {}).items():
        if col not in out.columns:
            continue
        if kind == "numeric":
            out[col] = to_numeric_series(out[col])
        elif kind == "text":
            out[col] = out[col].astype("string")
    return out


def outlier_mask(s: pd.Series, method: str = "iqr") -> tuple[pd.Series, float, float]:
    """Máscara booleana de atípicos y límites (inferior, superior)."""
    x = s.dropna()
    never = pd.Series(False, index=s.index)
    if len(x) < 4:
        return never, -np.inf, np.inf
    if method == "zscore":
        mu, sd = x.mean(), x.std(ddof=1)
        if sd == 0 or np.isnan(sd):
            return never, -np.inf, np.inf
        lo, hi = mu - 3 * sd, mu + 3 * sd
    else:  # IQR de Tukey
        q1, q3 = x.quantile(0.25), x.quantile(0.75)
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return ((s < lo) | (s > hi)).fillna(False), float(lo), float(hi)


def quality_report(df: pd.DataFrame, method: str = "iqr") -> list[dict]:
    rows = []
    for col in df.columns:
        is_num = pd.api.types.is_numeric_dtype(df[col])
        miss = int(df[col].isna().sum())
        out = int(outlier_mask(df[col], method)[0].sum()) if is_num else 0
        rows.append({
            "column": col,
            "dtype": "numérico" if is_num else "texto",
            "is_numeric": bool(is_num),
            "missing": miss,
            "missing_pct": round(100 * miss / len(df), 2) if len(df) else 0,
            "outliers": out,
        })
    return rows


def clean(df: pd.DataFrame, missing: str = "none", outliers: str = "none",
          method: str = "iqr", types: dict | None = None) -> tuple[pd.DataFrame, list[str]]:
    """Aplica la limpieza y devuelve (df limpio, bitácora de acciones)."""
    log: list[str] = []
    out = convert_types(df, types or {})
    if types:
        log.append(f"Conversión de tipos aplicada a {len(types)} columna(s).")
    start_rows = len(out)
    label_m = "IQR 1.5" if method == "iqr" else "Z > 3"

    # 1) Valores faltantes
    n_missing = int(out.isna().sum().sum())
    if missing == "drop":
        out = out.dropna()
        log.append(f"Se eliminaron {start_rows - len(out)} fila(s) con valores faltantes.")
    elif missing in ("mean", "median"):
        nums = numeric_columns(out)
        for col in nums:
            if out[col].isna().any():
                out[col] = out[col].fillna(out[col].mean() if missing == "mean" else out[col].median())
        for col in [c for c in out.columns if c not in nums]:
            if out[col].isna().any():
                mode = out[col].mode(dropna=True)
                if len(mode):
                    out[col] = out[col].fillna(mode.iloc[0])
        label = "media" if missing == "mean" else "mediana"
        log.append(f"Se imputaron {n_missing} valor(es) faltante(s) con la {label} (moda en texto).")
    elif n_missing:
        log.append(f"Se mantienen {n_missing} valor(es) faltante(s); el modelo usará solo filas completas.")

    # 2) Valores atípicos
    if outliers == "remove":
        keep = pd.Series(True, index=out.index)
        for col in numeric_columns(out):
            keep &= ~outlier_mask(out[col], method)[0]
        log.append(f"Se eliminaron {int((~keep).sum())} fila(s) con valores atípicos ({label_m}).")
        out = out[keep]
    elif outliers == "cap":
        capped = 0
        for col in numeric_columns(out):
            mask, lo, hi = outlier_mask(out[col], method)
            capped += int(mask.sum())
            out[col] = out[col].clip(lo, hi)
        log.append(f"Se limitaron {capped} valor(es) atípico(s) a los extremos ({label_m}).")

    out = out.reset_index(drop=True)
    if len(out) < 3:
        raise ValueError("La limpieza dejó menos de 3 filas. Prueba otra estrategia.")
    if not log:
        log.append("Sin cambios: se conservan los datos originales.")
    return out, log


def describe(df: pd.DataFrame) -> list[dict]:
    rows = []
    for col in numeric_columns(df):
        s = df[col].dropna()
        if s.empty:
            continue
        rows.append({
            "column": col,
            "n": int(s.size),
            "mean": float(s.mean()),
            "variance": float(s.var(ddof=1)) if s.size > 1 else 0.0,
            "std": float(s.std(ddof=1)) if s.size > 1 else 0.0,
            "min": float(s.min()),
            "q1": float(s.quantile(0.25)),
            "median": float(s.median()),
            "q3": float(s.quantile(0.75)),
            "max": float(s.max()),
        })
    return rows

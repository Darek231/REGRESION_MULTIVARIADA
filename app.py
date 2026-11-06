"""Sistema de Regresión Multivariada · Investigación Operativa II.

Ejecutar:  python app.py   ->  http://127.0.0.1:5000
"""
from __future__ import annotations

import math
import secrets
from collections import OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd
from flask import Flask, jsonify, render_template, request

from backend import cleaning, data_io, diagnostics, plots, regression

BASE = Path(__file__).resolve().parent
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024  # 15 MB

# Estado en memoria por sesión (suficiente para una práctica; máx. 20 sesiones)
STORE: "OrderedDict[str, dict]" = OrderedDict()
MAX_SESSIONS = 20


class ApiError(Exception):
    def __init__(self, msg: str, status: int = 400):
        super().__init__(msg)
        self.msg, self.status = msg, status


@app.errorhandler(ApiError)
def _api_error(e: ApiError):
    return jsonify({"error": e.msg}), e.status


@app.errorhandler(ValueError)
def _value_error(e: ValueError):
    return jsonify({"error": str(e)}), 400


@app.errorhandler(413)
def _too_big(_):
    return jsonify({"error": "El archivo supera el límite de 15 MB."}), 413


# --------------------------------------------------------------------- utilidades
def to_py(obj):
    """Convierte NumPy/pandas a tipos JSON válidos (NaN/inf -> None)."""
    if isinstance(obj, dict):
        return {k: to_py(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_py(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return [to_py(v) for v in obj.tolist()]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        v = float(obj)
        return v if math.isfinite(v) else None
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if obj is pd.NA:
        return None
    return obj


def ok(payload: dict):
    return jsonify(to_py(payload))


def get_session(token: str | None) -> dict:
    if not token or token not in STORE:
        raise ApiError("Sesión no encontrada. Vuelve a cargar tu archivo CSV.", 404)
    STORE.move_to_end(token)
    return STORE[token]


def new_session(df: pd.DataFrame, meta: dict, filename: str) -> str:
    token = secrets.token_urlsafe(12)
    STORE[token] = {"raw": df, "df": df, "meta": meta, "filename": filename, "fit": None}
    while len(STORE) > MAX_SESSIONS:
        STORE.popitem(last=False)
    return token


def preview_rows(df: pd.DataFrame, n: int = 10) -> list[list]:
    head = df.head(n).astype(object).where(df.head(n).notna(), None)
    return head.values.tolist()


def dataset_payload(token: str, log: list[str] | None = None) -> dict:
    s = get_session(token)
    df = s["df"]
    return {
        "token": token,
        "filename": s["filename"],
        "rows": int(df.shape[0]),
        "cols": int(df.shape[1]),
        "delimiter": s["meta"]["delimiter_label"],
        "renamed": s["meta"]["renamed"],
        "columns": list(df.columns),
        "numeric": cleaning.numeric_columns(df),
        "preview": preview_rows(df),
        "quality": cleaning.quality_report(df, s.get("method", "iqr")),
        "describe": cleaning.describe(df),
        "log": log or [],
    }


# --------------------------------------------------------------------- rutas
@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/upload")
def upload():
    f = request.files.get("file")
    if not f or not f.filename:
        raise ApiError("Selecciona un archivo CSV.")
    if not f.filename.lower().endswith((".csv", ".txt", ".tsv")):
        raise ApiError("El archivo debe tener formato CSV.")
    df, meta = data_io.read_csv_bytes(f.read())
    token = new_session(df, meta, f.filename)
    return ok(dataset_payload(token))


@app.get("/api/sample")
def sample():
    path = BASE / "data" / "viviendas_ejemplo.csv"
    if not path.exists():
        raise ApiError("No se encontró el archivo de ejemplo.", 404)
    df, meta = data_io.read_csv_bytes(path.read_bytes())
    token = new_session(df, meta, path.name)
    return ok(dataset_payload(token))


@app.post("/api/clean")
def clean_data():
    b = request.get_json(force=True, silent=True) or {}
    s = get_session(b.get("token"))
    method = b.get("method", "iqr")
    df, log = cleaning.clean(
        s["raw"],
        missing=b.get("missing", "none"),
        outliers=b.get("outliers", "none"),
        method=method,
        types=b.get("types") or {},
    )
    s["df"], s["method"], s["fit"] = df, method, None
    return ok(dataset_payload(b["token"], log))


@app.post("/api/fit")
def fit():
    b = request.get_json(force=True, silent=True) or {}
    s = get_session(b.get("token"))
    df: pd.DataFrame = s["df"]
    y, xs = b.get("y"), b.get("x") or []
    nums = cleaning.numeric_columns(df)
    if y not in nums:
        raise ApiError("Elige una variable dependiente (Y) numérica.")
    xs = [x for x in xs if x != y]
    if not xs:
        raise ApiError("Elige al menos una variable independiente (X).")
    bad = [x for x in xs if x not in nums]
    if bad:
        raise ApiError(f"Las variables {', '.join(bad)} no son numéricas. Conviértelas en el paso de limpieza.")

    sub = df[[y] + xs].replace([np.inf, -np.inf], np.nan).dropna()
    dropped = int(len(df) - len(sub))
    res = regression.fit_ols(sub[xs].to_numpy(float), sub[y].to_numpy(float), xs)
    s["fit"] = {"res": res, "y": y, "x": xs}

    out = res.summary()
    out.update({
        "y": y, "x": xs, "dropped_rows": dropped,
        "equation": f"{y} = " + " + ".join(
            [f"{res.beta[0]:.4g}"] + [f"{res.beta[i + 1]:.4g}·{x}" for i, x in enumerate(xs)]).replace("+ -", "− "),
    })
    return ok(out)


def _need_fit(token) -> dict:
    s = get_session(token)
    if not s["fit"]:
        raise ApiError("Primero estima el modelo (paso 04).")
    return s["fit"]


@app.post("/api/tests")
def tests():
    b = request.get_json(force=True, silent=True) or {}
    fit_state = _need_fit(b.get("token"))
    out = diagnostics.run_tests(fit_state["res"], b.get("normality", "all"), b.get("hetero", "all"))
    return ok(out)


@app.post("/api/plots")
def plots_data():
    b = request.get_json(force=True, silent=True) or {}
    fit_state = _need_fit(b.get("token"))
    data = plots.build_plots(fit_state["res"])
    data["y"] = fit_state["y"]
    return ok(data)


if __name__ == "__main__":
    app.run(debug=True, port=5000)

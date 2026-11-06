"""Módulo 1 · Carga de datos.

- Detección automática del delimitador.
- Validación / normalización de nombres de variables.
- Conversión automática de columnas numéricas.
"""
from __future__ import annotations

import io
import re
import unicodedata
from collections import Counter

import pandas as pd

CANDIDATES = [",", ";", "\t", "|"]
DELIM_LABELS = {",": "coma (,)", ";": "punto y coma (;)", "\t": "tabulador", "|": "barra (|)"}


def decode_bytes(raw: bytes) -> str:
    """Decodifica el archivo probando UTF-8 (con BOM) y luego Latin-1."""
    for enc in ("utf-8-sig", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def detect_delimiter(text: str) -> str:
    """Elige el delimitador cuyo conteo por línea sea más consistente."""
    lines = [ln for ln in text.splitlines() if ln.strip()][:25]
    if not lines:
        return ","
    best, best_score = ",", 0.0
    for cand in CANDIDATES:
        counts = [ln.count(cand) for ln in lines]
        mode, freq = Counter(counts).most_common(1)[0]
        score = (freq / len(lines)) * mode if mode > 0 else 0.0
        if score > best_score:
            best, best_score = cand, score
    return best


def _clean_name(name: str, idx: int) -> str:
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode()
    s = re.sub(r"\W+", "_", s.strip()).strip("_")
    if not s or s.lower().startswith("unnamed"):
        s = f"var_{idx + 1}"
    if s[0].isdigit():
        s = f"v_{s}"
    return s


def validate_names(columns) -> tuple[list[str], list[dict]]:
    """Devuelve nombres válidos y la lista de cambios aplicados."""
    new, changes, seen = [], [], Counter()
    for i, old in enumerate(columns):
        name = _clean_name(old, i)
        seen[name] += 1
        if seen[name] > 1:
            name = f"{name}_{seen[name]}"
        if name != str(old):
            changes.append({"old": str(old), "new": name})
        new.append(name)
    return new, changes


def to_numeric_series(s: pd.Series) -> pd.Series:
    """Convierte a numérico tolerando espacios y coma decimal ('3,14')."""
    if pd.api.types.is_numeric_dtype(s):
        return s
    t = s.astype("string").str.strip()
    t = t.str.replace(r"^(-?\d+),(\d+)$", r"\1.\2", regex=True)
    return pd.to_numeric(t, errors="coerce").astype("float64")


def auto_convert(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte columnas de texto a numéricas si >=90 % de los valores lo permiten."""
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_numeric_dtype(out[col]):
            continue
        conv = to_numeric_series(out[col])
        non_null = out[col].notna().sum()
        if non_null and conv.notna().sum() / non_null >= 0.9:
            out[col] = conv
    return out


def read_csv_bytes(raw: bytes) -> tuple[pd.DataFrame, dict]:
    text = decode_bytes(raw)
    if not text.strip():
        raise ValueError("El archivo está vacío.")
    delim = detect_delimiter(text)
    try:
        df = pd.read_csv(io.StringIO(text), sep=delim, skipinitialspace=True)
    except Exception as exc:  # pandas lanza varios tipos de error
        raise ValueError(f"No se pudo leer el CSV: {exc}") from exc
    df = df.dropna(axis=1, how="all").dropna(axis=0, how="all")
    if df.shape[1] < 2 or df.shape[0] < 3:
        raise ValueError("El CSV necesita al menos 2 columnas y 3 filas.")
    names, changes = validate_names(df.columns)
    df.columns = names
    df = auto_convert(df)
    meta = {
        "delimiter": delim,
        "delimiter_label": DELIM_LABELS[delim],
        "renamed": changes,
    }
    return df, meta

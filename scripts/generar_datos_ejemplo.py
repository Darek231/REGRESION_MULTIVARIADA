"""Genera data/viviendas_ejemplo.csv (semilla fija, reproducible).

Y  = precio_miles (miles de USD)
Xs = area_m2, habitaciones, banos, antiguedad, distancia_centro_km, calidad_barrio
+  area_pies2 (casi idéntica a area_m2) -> sirve para demostrar VIF > 10.
Incluye valores faltantes y atípicos a propósito para probar la limpieza,
y varianza creciente con el área para que Breusch-Pagan/White tengan algo que detectar.
"""
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(2026)
n = 220

area = rng.normal(120, 35, n).clip(45, 260).round(1)
hab = np.clip((area / 35 + rng.normal(0, 0.7, n)).round(), 1, 7)
banos = np.clip((hab / 2 + rng.normal(0.4, 0.6, n)).round(), 1, 5)
antig = rng.gamma(2.2, 8, n).clip(0, 60).round(0)
dist = rng.gamma(2.0, 3.0, n).clip(0.3, 25).round(1)
barrio = np.clip(rng.normal(6.2, 1.8, n).round(), 1, 10)

ruido = rng.normal(0, 1, n) * (8 + 0.28 * area)          # heterocedasticidad
precio = (35 + 1.55 * area + 9.0 * hab + 14.0 * banos
          - 1.25 * antig - 3.4 * dist + 11.0 * barrio + ruido)

df = pd.DataFrame({
    "precio_miles": precio.round(1),
    "area_m2": area,
    "habitaciones": hab.astype(int),
    "banos": banos.astype(int),
    "antiguedad": antig.astype(int),
    "distancia_centro_km": dist,
    "calidad_barrio": barrio.astype(int),
    "area_pies2": (area * 10.7639 + rng.normal(0, 6, n)).round(1),
})

# Atípicos y faltantes (para practicar la limpieza)
for idx in rng.choice(n, 4, replace=False):
    df.loc[idx, "precio_miles"] = round(df.loc[idx, "precio_miles"] * 2.6, 1)
for col, k in [("antiguedad", 6), ("distancia_centro_km", 5), ("calidad_barrio", 4), ("area_m2", 3)]:
    df.loc[rng.choice(n, k, replace=False), col] = np.nan

out = Path(__file__).resolve().parent.parent / "data" / "viviendas_ejemplo.csv"
df.to_csv(out, index=False)
print(f"OK -> {out}  ({df.shape[0]} filas, {df.shape[1]} columnas)")

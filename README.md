# Constela · Sistema de Regresión Multivariada
Práctica de **Investigación Operativa II** — regresión lineal múltiple (OLS) con limpieza, validación estadística y gráficos.
Backend en **Python (Flask + NumPy/SciPy/pandas)** y frontend web (HTML/CSS/JS puro, sin frameworks) con el diseño oscuro de *Dala*.

## Ejecutar
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py                    # abre http://127.0.0.1:5000
pytest -q                        # (opcional) 11 pruebas del backend
```
Pulsa **«Usar datos de ejemplo»** (220 viviendas, 8 variables) o sube tu propio CSV.

## Estructura
```
├── app.py                  # Servidor Flask + API REST (/api/upload, clean, fit, tests, plots)
├── backend/
│   ├── data_io.py          # Carga CSV: delimitador automático, validación de nombres, tipos
│   ├── cleaning.py         # Faltantes, atípicos (IQR / Z), conversión de tipos, estadísticas descriptivas
│   ├── regression.py       # OLS: β, error estándar, t, p-valor, R², F, IC 95 %
│   ├── diagnostics.py      # Shapiro/KS/Jarque-Bera, Durbin-Watson, Breusch-Pagan/White, VIF
│   └── plots.py            # Datos de los 4 tipos de gráfico
├── templates/index.html    # Interfaz (6 pasos)
├── static/css/styles.css   # Tokens y estilos Dala (negro, violeta, ámbar)
├── static/js/              # particles.js (hero) · charts.js (gráficos canvas) · app.js (lógica)
├── data/viviendas_ejemplo.csv
├── scripts/generar_datos_ejemplo.py
└── tests/test_system.py
```

## Cumplimiento de la guía
| Guía | Dónde |
|---|---|
| Carga CSV, vista previa, delimitador automático, validación de nombres | Paso 01 · `data_io.py` |
| Faltantes, atípicos, conversión de tipos | Paso 02 · `cleaning.py` |
| Media, varianza, mín/máx, cuartiles | Paso 03 |
| β, error estándar, t, p-valor | Paso 04 · `regression.py` |
| Normalidad (3 tests), Durbin-Watson, Breusch-Pagan **y** White, VIF (>10 resaltado) | Paso 05 · `diagnostics.py` |
| Dispersión Xᵢ vs Y, histograma, Q-Q, residuos estándar vs ajustados (descargables en PNG) | Paso 06 · `charts.js` |
| Selección de Y y X, ejecución y resultados en pantalla | Pasos 04–05 |

## Para probar el flujo con el ejemplo
1. En **Limpieza** elige *Imputar mediana* + *Eliminar filas* de atípicos → R² sube de ~0.43 a ~0.78 y los residuos pasan a ser normales.
2. En **Validación** verás `area_m2` y `area_pies2` con VIF ≈ 190 (son la misma variable en distintas unidades). Quita una en el paso 04 y el VIF baja a ~1–4.

## Notas técnicas
- Los residuos «estándar» son internamente estudentizados: e / (s·√(1−hᵢᵢ)).
- Durbin-Watson usa la regla práctica d<1.5 (+), 1.5–2.5 (sin autocorrelación), d>2.5 (−); requiere datos con orden natural.
- Breusch-Pagan usa la versión de Koenker (LM = n·R²). White incluye cuadrados y productos cruzados.
- Los datos viven en memoria del servidor (máx. 20 sesiones); no se guarda nada en disco.
- La fuente se carga de Google Fonts (Inter, sustituto de PPNeueMontreal); sin internet se usa la fuente del sistema.

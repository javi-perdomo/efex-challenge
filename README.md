# EFEX AI — Broker Copilot

Sistema de inteligencia artificial para detección de oportunidades comerciales y generación de mensajes personalizados para brokers FX de EFEX.

---

## Problema de negocio

EFEX es una fintech especializada en cambio de divisas (FX) entre México y Estados Unidos. Opera a través de una red de brokers/promotores independientes que administran carteras de clientes corporativos y personas físicas que realizan operaciones de FX de forma recurrente.

**El problema:** Los brokers tienen entre 5 y 50 clientes activos, pero no cuentan con herramientas que les ayuden a:

1. **Detectar a tiempo** cuándo un cliente está en riesgo de irse (churn silencioso)
2. **Identificar** qué clientes inactivos tienen potencial real de reactivación
3. **Capitalizar** momentos de crecimiento para hacer upsell
4. **Saber cuándo y cómo** contactar a cada cliente de forma efectiva

El resultado es pérdida de volumen, ingresos no capturados y alta dependencia de la intuición del broker.

**La solución:** EFEX AI es un sistema que analiza el historial transaccional completo, segmenta automáticamente a cada cliente con RFM scoring, detecta oportunidades por tipo y genera mensajes de WhatsApp accionables para cada broker — con IA local (Ollama) o templates de fallback.

---

## Arquitectura del sistema

```
transactions_anonymized.xlsx (176k filas)
        │
        ▼
  ┌─────────────┐      ┌──────────────────────┐      ┌──────────────────────┐
  │   eda.py    │      │     features.py       │      │   churn_model.py     │
  │ Exploración │      │ Feature Engineering   │      │ XGBoost ML Model     │
  │ + 4 plots   │      │ + RFM Scoring         │      │ ROC-AUC 0.963        │
  └─────────────┘      └──────────┬───────────┘      └──────────┬───────────┘
                                  │ features.parquet             │ churn_scores.parquet
                                  ▼                              │
                       ┌──────────────────────┐                  │
                       │   opportunities.py    │                  │
                       │  Motor de Reglas      │                  │
                       │  CHURN / REACT /      │                  │
                       │  UPSELL / BEST_TIME   │                  │
                       └──────────┬───────────┘                  │
                                  │ opportunities.parquet         │
                    ┌─────────────┴──────────────────────────────┘
                    ▼                            ▼
         ┌─────────────────┐          ┌──────────────────────┐
         │  message_       │          │       app.py          │
         │  generator.py   │◄────────►│  Streamlit Dashboard  │
         │  Ollama LLM /   │          │  Tab 1: Oportunidades │
         │  Templates      │          │  Tab 2: Mensajes WA   │
         └─────────────────┘          │  Tab 3: Análisis      │
                                      └──────────────────────┘
```

### Componentes principales

| Archivo | Responsabilidad |
|---|---|
| `eda.py` | Análisis exploratorio, estadísticas descriptivas, 4 plots |
| `features.py` | Feature engineering por cliente: recencia, frecuencia, volumen, tendencia, spread, horario preferido + RFM scoring + segmentación |
| `opportunities.py` | Motor de reglas: detecta CHURN_RISK, REACTIVATION, UPSELL, BEST_TIME por broker |
| `churn_model.py` | Modelo XGBoost de propensión a churn con validación cruzada (ROC-AUC 0.963) |
| `message_generator.py` | Genera mensajes WhatsApp con Ollama (llama3.2/mistral) o templates de fallback |
| `architecture.py` | Genera diagrama de arquitectura PNG |
| `app.py` | Dashboard Streamlit completo con 3 tabs |

---

## Funcionalidades del Dashboard

### Sidebar — Selector de broker

- Lista todos los brokers disponibles con nombre y número de oportunidades activas
- Muestra KPIs del broker seleccionado: volumen total, clientes activos, clientes en riesgo, oportunidades de alta prioridad
- Botón **"Generar mensajes con IA"** para lanzar generación masiva de mensajes WhatsApp

---

### Tab 1 — Oportunidades

Vista principal de oportunidades comerciales detectadas para el broker seleccionado.


#### Tabla de oportunidades
Columnas:
| Columna | Descripción |
|---|---|
| Cliente | Nombre del cliente |
| Tipo | Tipo de oportunidad con emoji y etiqueta legible |
| Prioridad | Alta / Media / Baja |
| Días inactivo | Días desde la última transacción |
| Volumen Total | Volumen acumulado histórico en USD |
| **Riesgo Churn 🤖** | Barra de progreso 0–100% con probabilidad de abandono (XGBoost, ROC-AUC 0.96) |

#### Filtros
- **Por prioridad**: multiselect (Alta / Media / Baja)
- **Por tipo**: multiselect (Riesgo de Pérdida / Recuperar Cliente / Crecer Cuenta / Ventana de Contacto)

#### Tipos de oportunidad

| Tipo | Criterio de detección | Prioridad |
|---|---|---|
| 🚨 **Riesgo de Pérdida** | Cliente en segmento `en_riesgo` | Alta si volumen > p75, Media si no |
| 💤 **Recuperar Cliente** | Segmento `reactivar` con volumen > mediana | Media |
| 📈 **Crecer Cuenta** | Segmento `activo_sano` con tendencia positiva O ≥5 transacciones en 90d | Alta si tendencia + frecuencia altas |
| 🎯 **Ventana de Contacto** | Todos los clientes activos o en riesgo | Baja |

---

### Tab 2 — Mensajes WhatsApp

Vista de mensajes generados para cada cliente del broker.

#### Generación de mensajes
- **Con IA (Ollama)**: genera mensajes personalizados en español usando llama3.2 o mistral (LLM local, sin costo, sin enviar datos a servicios externos)
- **Con templates**: fallback automático estructurado cuando Ollama no está disponible
- **Progress bar en tiempo real**: muestra el avance `[N/Total] cliente — tipo — fuente` durante la generación
- **Modal de alerta**: si Ollama no tiene modelos disponibles, alerta al usuario con instrucciones de instalación y opción de continuar con templates

#### Visualización de mensajes
- Burbujas estilo WhatsApp con fondo verde y timestamp
- Badge de tipo de oportunidad con color e ícono
- Etiqueta de fuente: `🤖 IA` o `📝 Template`
- Filtros por tipo de oportunidad y prioridad

---

### Tab 3 — Análisis del Broker

Análisis detallado del portafolio del broker seleccionado.

#### KPIs principales
- 💰 Volumen total acumulado (USD)
- 👥 Número de clientes activos
- 📊 Transacciones completadas
- ⚡ Promedio de transacciones por cliente

#### Gráficas
- **Distribución por segmento RFM**: dona con colores por segmento
- **Top 10 clientes por volumen**: barras horizontales con color por segmento
- **Evolución de volumen**: serie de tiempo mensual con área sombreada (si hay transacciones disponibles)
- **Mapa de calor de actividad**: hora del día vs. día de la semana, muestra cuándo opera más cada broker

#### Estado de clientes
Tabla completa de todos los clientes del broker con:

| Columna | Descripción |
|---|---|
| Cliente | Nombre del cliente |
| Estado | Semáforo: 🟢 Activo / 🟡 Atención / 🟠 Inactivo / 🔴 Sin actividad |
| Segmento | Etiqueta RFM: Cliente Activo / En Riesgo de Irse / Dormido–Recuperable / Sin Actividad Reciente |
| Días inactivo | Días desde la última transacción |
| Txs 30d | Transacciones en los últimos 30 días |
| Txs 90d | Transacciones en los últimos 90 días |
| Volumen total | Volumen acumulado en USD |
| Tendencia | 📈 Fuerte alza / ↗️ Creciendo / ➡️ Estable / ↘️ Bajando / 📉 Caída fuerte |
| Mejor contacto | Día y hora preferida (ej. "Martes a las 10:00") |
| **Riesgo Churn 🤖** | Barra de progreso 0–100% con probabilidad XGBoost de abandono |

---

## Modelo de ML — Propensión a Churn

Modelo XGBoost entrenado con validación cruzada estratificada (5-fold) para predecir la probabilidad de que un cliente abandone EFEX.

### Definición de churn
Un cliente se considera "churned" si:
- Tenía **≥ 2 transacciones** antes de la fecha de corte (90 días antes del máximo histórico)
- **No realizó ninguna transacción** en los últimos 90 días del dataset

### Features utilizadas (sin data leakage)
| Feature | Descripción |
|---|---|
| `tx_count_total` | Volumen histórico total de transacciones |
| `tx_count_completed` | Transacciones completadas exitosamente |
| `success_rate` | Ratio de éxito histórico |
| `avg_volume_usd` | Ticket promedio por transacción |
| `total_volume_usd` | Volumen acumulado total en USD |
| `volume_trend` | Tendencia de volumen (regresión lineal 8 semanas previas al corte) |
| `avg_spread_bps` | Spread promedio pagado en bps |
| `spread_vs_minimum` | Margen sobre el spread mínimo |
| `preferred_hour` | Hora preferida de operación |
| `preferred_day` | Día preferido de operación |

> **Nota:** Se excluyen explícitamente `days_since_last_tx`, `tx_count_30d` y `tx_count_90d` para evitar data leakage (estos features codifican directamente el label).

### Métricas
| Métrica | Valor |
|---|---|
| ROC-AUC (CV-5) | **0.963** |
| Avg. Precision | **0.950** |
| Accuracy | ~90% |

### Outputs del modelo
| Archivo | Contenido |
|---|---|
| `outputs/churn_model.pkl` | Modelo entrenado serializado |
| `outputs/churn_scores.parquet` | Probabilidad de churn por cliente (0.0–1.0) + score 0–100 + etiqueta de riesgo |
| `outputs/churn_report.txt` | Métricas, classification report y feature importance |

### Etiquetas de riesgo
| Rango | Etiqueta |
|---|---|
| 0–30% | Bajo |
| 30–60% | Medio |
| 60–80% | Alto |
| 80–100% | Crítico |

---

## Segmentación RFM

El sistema clasifica automáticamente a cada cliente en 4 segmentos usando scoring RFM (Recency, Frequency, Monetary) con cuartiles del dataset.

| Segmento | Criterio | Acción recomendada |
|---|---|---|
| ✅ **Cliente Activo** (`activo_sano`) | RFM score ≥ 9, o score ≥ 6 y activo en últimos 45 días | Upsell / fidelización |
| ⚠️ **En Riesgo de Irse** (`en_riesgo`) | Score moderado con inactividad reciente | Contacto urgente |
| 💤 **Dormido — Recuperable** (`reactivar`) | Inactivo 30–180 días con historial valioso | Campaña de reactivación |
| ❌ **Sin Actividad Reciente** (`perdido`) | Sin transacciones en más de 180 días | Esfuerzo bajo / descarte |

---

## Instalación

### Requisitos del sistema

| Requisito | Versión mínima | Notas |
|---|---|---|
| Python | 3.10+ | Recomendado: 3.11 o 3.12 |
| RAM | 4 GB | 8 GB recomendado con Ollama activo |
| Disco | 500 MB | + 2–4 GB si se instala Ollama con modelo |
| OS | macOS / Linux / Windows | Probado en macOS Sequoia |

### Dependencias Python

Las siguientes librerías se instalan automáticamente con `pip install -r requirements.txt`:

| Librería | Versión | Uso |
|---|---|---|
| `streamlit` | 1.40.2 | Dashboard interactivo |
| `pandas` | 2.2.3 | Procesamiento de datos |
| `numpy` | 1.26.4 | Cálculos numéricos |
| `plotly` | 5.24.1 | Gráficas interactivas |
| `scikit-learn` | 1.5.2 | Cross-validation, métricas ML |
| `scipy` | 1.14.1 | Regresión lineal para volume_trend |
| `pyarrow` | 17.0.0 | Lectura/escritura de Parquet |
| `openpyxl` | 3.1.5 | Lectura del Excel de transacciones |
| `requests` | 2.32.3 | Comunicación con Ollama API |
| `matplotlib` | 3.9.2 | Plots del EDA |

> **XGBoost (modelo de churn):** Se instala por separado. Ver instrucciones abajo.

### Dependencias del sistema (macOS)

```bash
# XGBoost requiere libomp en macOS (OpenMP runtime)
brew install libomp

# Luego instalar xgboost
pip install xgboost
```

> En Linux/Windows `pip install xgboost` funciona directamente sin dependencias adicionales.


### Instalación de Ollama

Ollama permite generar mensajes personalizados con un LLM local sin costo ni API externa. Si no se instala, el sistema usa templates estructurados automáticamente.

```bash
# macOS — instalar Ollama
brew install ollama
# o descargar desde: https://ollama.ai/download

# Iniciar el servidor Ollama (dejarlo corriendo en segundo plano)
ollama serve

# En otra terminal, descargar un modelo (solo se hace una vez):
ollama pull llama3.2   # Recomendado: ~2 GB, rápido

# Verificar que el servidor responde
curl http://localhost:11434/api/tags
```

> **Nota:** Si Ollama no está disponible al generar mensajes, el dashboard muestra un modal con instrucciones y ofrece continuar con templates estructurados. No hay pérdida de funcionalidad.

### Verificación de instalación

```bash
# Verificar Python y dependencias
python --version          # >= 3.10
python -c "import streamlit, pandas, xgboost; print('OK')"

# Verificar Ollama (opcional)
curl -s http://localhost:11434/api/tags | python -c "import sys,json; print([m['name'] for m in json.load(sys.stdin).get('models',[])])"
```

---

## Cómo ejecutar

### Opción 1: Pipeline completo paso a paso

```bash
# Paso 1: EDA (genera outputs/eda/*.png)
python eda.py

# Paso 2: Feature engineering (genera outputs/features.parquet)
python features.py

# Paso 3: Detectar oportunidades (genera outputs/opportunities.parquet)
python opportunities.py

# Paso 4: Entrenar modelo de churn (genera outputs/churn_scores.parquet)
python churn_model.py

# Paso 5: Generar mensajes para un broker específico
python message_generator.py <broker_uuid>

# Paso 6: Lanzar dashboard
streamlit run app.py
```

### Opción 2: Solo el dashboard (genera todo automáticamente)

```bash
streamlit run app.py
```

El dashboard detecta si los archivos existen. Si no, los genera automáticamente al cargarse (~2 minutos la primera vez con 176k filas).

> **Nota:** El modelo de churn (`churn_scores.parquet`) debe generarse manualmente con `python churn_model.py` antes de lanzar el dashboard para que aparezca la columna de riesgo ML.

### Acceso al dashboard

```
http://localhost:8501
```

---

## Decisiones técnicas y trade-offs

### 1. Cálculo de `volume_usd`

```python
volume_usd = pd.to_numeric(balance_paid, errors='coerce') * er_paid_to_usd / 1e8
```

**Por qué:** La columna `balance_paid` contiene tipos mixtos. `pd.to_numeric(..., errors='coerce')` convierte lo que puede y silencia el resto. El factor `/1e8` des-escala el valor almacenado.

**Trade-off:** Se pierden filas con `balance_paid` no parseable, pero la alternativa es frágil.

### 2. Detección de broker (`intermediary_name`)

```python
df['has_broker'] = df['intermediary_name'].apply(lambda x: isinstance(x, str) and len(x) > 0)
```

**Por qué:** Excel puede leer celdas vacías como `None`, `True`, `False` o `NaN`. Un `isinstance(x, str)` es el único filtro robusto.

### 3. Fecha de referencia = `max(trigger_at_dt)`

**Por qué:** El dataset tiene una fecha máxima histórica. Usar `datetime.now()` haría que toda la recencia sea inútil ya que los datos no son en tiempo real.

**Trade-off:** El sistema no funciona en producción sin un mecanismo de actualización del dataset.

### 4. RFM scoring con cuartiles

**Por qué:** Los umbrales fijos son arbitrarios y frágiles ante distribuciones skewed (volumen: mediana $4,601, media $20,559).

**Trade-off:** Los scores no son comparables entre datasets de épocas distintas. Para producción, guardar los percentiles como parámetros del modelo.

### 5. Motor de oportunidades basado en reglas

**Por qué:** No hay etiquetas de churn real históricas. Las reglas son transparentes y auditables por el equipo de negocio.

**Trade-off:** No captura patrones complejos. Complementado con el modelo XGBoost de propensión a churn.

### 6. XGBoost sin data leakage

Se excluyen `days_since_last_tx`, `tx_count_30d` y `tx_count_90d` del modelo porque codifican directamente el label de churn (churned = 0 transacciones en los últimos 90 días).

**Resultado:** ROC-AUC realista de 0.963 vs. 1.000 con data leakage.

### 7. Ollama como LLM local con fallback a templates

**Por qué:**
- Sin costo operativo (OpenAI API podría costar $0.001–0.01 por mensaje)
- Privacidad: los datos de clientes no salen del servidor
- Latencia predecible: ~2–8 segundos por mensaje

**Trade-off:** Llama3.2 en local puede ser más lento que GPT-4o en la nube.

### 8. Broker DIRECTO

Clientes sin `intermediary_uuid` se agrupan bajo el broker "DIRECTO". Para este broker, las transacciones no pueden filtrarse por `intermediary_uuid`, por lo que el Tab 3 usa los datos agregados de `features.parquet` como fallback.

---

## Herramientas de IA utilizadas

### Claude Code (Anthropic) — herramienta principal de desarrollo

Este POC fue desarrollado íntegramente con **Claude Code** (`claude-sonnet-4-6`), el CLI oficial de Anthropic para desarrollo de software asistido por IA. Se usó para diseño de arquitectura, feature engineering, implementación del modelo ML, corrección de bugs y generación del dashboard.

**Tareas realizadas con Claude Code:**

| Tarea | Descripción |
|---|---|
| Análisis del dataset | Diagnóstico de columnas con tipos mixtos, parsing de fechas UTC, detección de broker DIRECTO |
| Feature engineering | Diseño de 10 features de comportamiento: recencia, frecuencia, volumen, tendencia (regresión lineal), spread, horario preferido |
| Segmentación RFM | Scoring con cuartiles del dataset real, clasificación en 4 segmentos, calibración del umbral de "perdido" |
| Motor de oportunidades | Reglas de detección CHURN_RISK, REACTIVATION, UPSELL, BEST_TIME con priorización por volumen |
| Modelo XGBoost | Construcción sin data leakage, StratifiedKFold CV-5, integración de scores al dashboard |
| Dashboard Streamlit | 3 tabs completos, gráficas Plotly, modal de Ollama, progress bar, columna ProgressColumn |
| Debugging | Fix de DuplicateElementId, gráfica de dona 100% churn, UPSELL=0, análisis DIRECTO vacío |
| PDF ejecutivo | Generación programática con fpdf2 de reporte de 7 páginas de impacto de negocio |

**Prompts clave utilizados:**

```
1. "Tengo un archivo Excel de transacciones FX con 176k filas y 51 columnas.
   La columna balance_paid tiene tipos mixtos. intermediary_name cuando es nulo
   pandas lo lee como True. Ayúdame a diseñar el pipeline de limpieza."

2. "Diseña features de comportamiento por cliente para detectar churn en una
   fintech FX: recencia, frecuencia, volumen, tendencia de volumen con regresión
   lineal, horario preferido de operación."

3. "Implementa RFM scoring con cuartiles del dataset real. Define segmentos:
   activo_sano, en_riesgo, reactivar, perdido. Usa la fecha máxima del dataset
   como referencia, no datetime.now()."

4. "El modelo de churn tiene ROC-AUC 1.000. ¿Hay data leakage? Revisa las
   features y corrígelo."

5. "Crea un dashboard Streamlit production-quality con sidebar de brokers,
   3 tabs (oportunidades con barra de churn ML, mensajes WhatsApp con burbuja
   visual, análisis con heatmap de actividad), filtros de prioridad, modal
   de alerta Ollama y progress bar durante la generación de mensajes."
```

### Ollama + Meta Llama 3.2 / Mistral — LLM local para mensajes

LLM ejecutado completamente on-premise para la generación de mensajes WhatsApp personalizados. Sin envío de datos a servidores externos, sin costo por llamada de API.

- **Modelo preferido:** `llama3.2` (2 GB, rápido, excelente en español)
- **Modelo alternativo:** `mistral` (4 GB, mayor calidad)
- **Fallback automático:** templates estructurados cuando Ollama no está disponible

---

## Métricas de éxito propuestas

### Métricas de adopción (primeros 30 días)

| Métrica | Baseline | Objetivo |
|---|---|---|
| Brokers que abren el dashboard ≥1x/semana | 0% | 60% |
| Mensajes WhatsApp generados/semana | 0 | 500+ |
| Tiempo broker → acción sobre oportunidad | No medido | < 2 horas |

### Métricas de impacto de negocio (90 días)

| Métrica | Cómo medir | Objetivo |
|---|---|---|
| Tasa de churn en clientes `en_riesgo` | Comparar con grupo control sin SWAT | Reducir 25% |
| Tasa de reactivación `reactivar` | % que opera de nuevo en 30 días | > 15% |
| Volumen en clientes UPSELL | Incremento vs. período anterior | +20% por cliente |
| Precisión de segmentación | Validación manual por brokers | > 75% acuerdo |

### Métricas técnicas

| Métrica | Objetivo |
|---|---|
| Tiempo de carga (primera vez) | < 3 minutos |
| Tiempo de generación de mensajes | < 60s (templates) / < 5min (Ollama) |
| Cobertura de clientes segmentados | 100% de clientes con ≥1 transacción |
| ROC-AUC modelo churn | > 0.90 |

---

## Estructura de archivos

```
efex-ai-challenge/
├── transactions_anonymized.xlsx    # Datos fuente (no incluido en repo)
├── eda.py                          # Análisis exploratorio
├── features.py                     # Feature engineering + RFM
├── opportunities.py                # Motor de oportunidades
├── churn_model.py                  # Modelo ML XGBoost de propensión a churn
├── message_generator.py            # Generador de mensajes con LLM
├── architecture.py                 # Diagrama de arquitectura
├── app.py                          # Dashboard Streamlit
├── requirements.txt                # Dependencias Python
├── README.md                       # Este archivo
└── outputs/
    ├── eda/
    │   ├── distribucion_volumen.png
    │   ├── top_brokers_revenue.png
    │   ├── distribucion_status.png
    │   └── clientes_por_broker.png
    ├── features.parquet            # Features por cliente (836 clientes)
    ├── opportunities.parquet       # Oportunidades detectadas (1,024+)
    ├── churn_model.pkl             # Modelo XGBoost serializado
    ├── churn_scores.parquet        # Probabilidad de churn por cliente
    ├── churn_report.txt            # Métricas y feature importance
    ├── messages.json               # Mensajes generados por broker
    └── architecture.png            # Diagrama del sistema
```

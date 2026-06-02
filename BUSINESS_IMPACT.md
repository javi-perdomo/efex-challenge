# EFEX AI — Business Impact Report
**Junio 2026 · Confidencial**

---

## Resumen ejecutivo

Sistema de inteligencia artificial que analiza 176,000+ transacciones FX para convertir datos en recomendaciones comerciales concretas para brokers. Detecta clientes en riesgo de abandono, identifica oportunidades de reactivación y upsell, y genera mensajes de WhatsApp personalizados con IA local.

| Dato | Valor |
|---|---|
| Dataset analizado | 176,000+ transacciones / 836 clientes / 99 brokers |
| Oportunidades detectadas | 1,024 priorizadas por volumen |
| Modelo de churn | XGBoost · ROC-AUC 0.963 |
| Generación de mensajes | LLM local (Llama 3.2) + fallback a templates |

---

## El problema

Los brokers administran carteras de 5 a 50 clientes sin herramientas de seguimiento:

- **Churn silencioso**: el broker detecta la baja semanas tarde, cuando el cliente ya opera con otro.
- **Reactivación sin datos**: no saben qué clientes inactivos vale la pena recuperar ni cuándo contactarlos.
- **Upsell invisible**: clientes con tendencia de crecimiento nunca se capitalizan a tiempo.
- **Mensajes genéricos**: 1–2 horas por semana redactando el mismo mensaje para todos.

---

## La solución

Cuatro componentes integrados en un dashboard Streamlit:

**1. Segmentación automática (RFM)**
Clasifica cada cliente en 4 segmentos usando 10 features de comportamiento. Se recalcula en cada ejecución con cuartiles del dataset real.

**2. Motor de oportunidades**
Detecta 4 tipos de alertas: Riesgo de Pérdida, Recuperar Cliente, Crecer Cuenta y Ventana de Contacto. Priorizadas por impacto en volumen USD.

**3. Modelo de churn XGBoost**
Probabilidad de abandono 0–100% por cliente. ROC-AUC 0.963 con cross-validation de 5 folds. Sin data leakage. Visible en el dashboard como barra de progreso.

**4. Mensajes WhatsApp con IA**
LLM local (Llama 3.2 vía Ollama). Sin costo de API. Sin envío de datos externos. Fallback automático a templates. Generación en menos de 60 segundos por cartera.

---

## Impacto por funcionalidad

| Funcionalidad | Sin el sistema | Con EFEX AI |
|---|---|---|
| Detección de churn | Se detecta semanas tarde | Alerta con probabilidad ML 0–100% |
| Segmentación de clientes | Manual, sin criterio uniforme | 836 clientes en 4 segmentos en < 2 min |
| Priorizar contactos | Por intuición | 1,024 oportunidades ordenadas por volumen |
| Mensajes WhatsApp | 1–2h redactando por cartera | Mensajes personalizados en < 60 segundos |
| Momento de contacto | Horario genérico o aleatorio | Día y hora óptima por cliente (histórico) |
| Visión del portafolio | Sin datos ni dashboard | KPIs, tendencias y heatmap de actividad |

---

## ROI proyectado (escenario conservador, 90 días)

**Supuestos:**
- 60 de 99 brokers adoptando el sistema (60%)
- 2 clientes en riesgo salvados por broker por mes
- Volumen promedio por cliente: $45,000 USD (percentil 50 del dataset)
- Spread promedio: 35 bps
- 1 cliente reactivado por broker por mes
- +20% de ticket en clientes activos con tendencia positiva

**Resultados:**

| Métrica | Valor | Cálculo |
|---|---|---|
| Volumen recuperado (churn evitado) | $162M USD | 60 brokers × 2 clientes × $45K × 3 meses |
| Revenue adicional (spread) | $56,700 USD | Volumen recuperado × 35 bps |
| Volumen en upsell | $54M USD | 431 activos × +20% ticket × 3 meses |
| Reducción tiempo mensajes | > 95% | De 1–2h a < 60 segundos por broker |

---

## El modelo de machine learning

**Definición de churn:** cliente con ≥ 2 transacciones históricas y ninguna en los últimos 90 días.

**Features utilizadas** (sin data leakage):
- `tx_count_total`, `tx_count_completed`, `success_rate`
- `avg_volume_usd`, `total_volume_usd`, `volume_trend`
- `avg_spread_bps`, `spread_vs_minimum`
- `preferred_hour`, `preferred_day`

> Se excluyen `days_since_last_tx`, `tx_count_30d` y `tx_count_90d` porque codifican directamente el label. Con ellas el ROC-AUC es artificialmente 1.000; sin ellas: **0.963 real**.

| Métrica | Valor |
|---|---|
| ROC-AUC (CV-5) | 0.963 |
| Avg. Precision | 0.950 |
| Accuracy | ~90% |
| Clientes scored | 836 (100% del portafolio) |

---

## Segmentación RFM

| Segmento | Criterio | Acción |
|---|---|---|
| ✅ Cliente Activo (`activo_sano`) | RFM score ≥ 9 | Upsell — aumentar ticket o frecuencia |
| ⚠️ En Riesgo de Irse (`en_riesgo`) | Score moderado + desaceleración reciente | Contacto urgente |
| 💤 Dormido — Recuperable (`reactivar`) | Inactivo 30–180 días con historial valioso | Campaña de reactivación |
| ❌ Sin Actividad Reciente (`perdido`) | Sin transacciones en > 180 días | Esfuerzo mínimo |

---

## Métricas de éxito

**Adopción — primeros 30 días:**

| Métrica | Objetivo |
|---|---|
| Brokers activos en dashboard (≥ 1×/semana) | 60% |
| Mensajes WhatsApp generados / semana | 500+ |
| Tiempo broker → acción sobre alerta | < 2 horas |
| Acuerdo con segmentación (validación manual) | > 75% |

**Impacto de negocio — 90 días:**

| Métrica | Objetivo |
|---|---|
| Churn rate en clientes `en_riesgo` | Reducir 25% |
| Tasa de reactivación `reactivar` | > 15% en < 30 días |
| Upsell por cliente activo | +20% ticket |

---

## Roadmap

**Fase 1 — POC (hoy)**
Dashboard completo con segmentación RFM, 1,024 oportunidades, modelo XGBoost y generación de mensajes con LLM local. Cobertura total: 99 brokers, 836 clientes.

**Fase 2 — Producción (30–60 días)**
Autenticación OAuth por broker, pipeline diario automatizado, API REST para WhatsApp Business, notificaciones push ante alertas de alta prioridad.

**Fase 3 — Escala (60–120 días)**
Modelo de supervivencia (Kaplan-Meier), A/B testing de mensajes, integración con CRM, panel ejecutivo con KPIs en tiempo real.

---

*EFEX AI · Junio 2026 · Confidencial*

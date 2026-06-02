"""
Modelo de ML — Propensión a Churn
===================================
Etiqueta: cliente "churned" si tenía actividad antes de una fecha de corte
          pero ninguna transacción en los 90 días previos a la fecha de referencia.

Features: comportamiento transaccional por cliente (features.parquet)
Model: XGBoost con validación cruzada estratificada
Output:
  outputs/churn_model.pkl       — modelo entrenado
  outputs/churn_scores.parquet  — churn_probability por cliente (0.0–1.0)
  outputs/churn_report.txt      — métricas y feature importance

Run: python churn_model.py
"""

import pandas as pd
import numpy as np
import os
import pickle
import warnings
warnings.filterwarnings('ignore')

# ── Constantes ────────────────────────────────────────────────────────────────
CHURN_WINDOW_DAYS  = 90    # ventana para definir "churned"
MIN_PAST_TXS       = 2     # mínimo de transacciones pasadas para incluir al cliente
OUTPUT_DIR         = 'outputs'
MODEL_PATH         = f'{OUTPUT_DIR}/churn_model.pkl'
SCORES_PATH        = f'{OUTPUT_DIR}/churn_scores.parquet'
REPORT_PATH        = f'{OUTPUT_DIR}/churn_report.txt'


# IMPORTANTE: excluimos features que filtrarían el label directamente:
# - days_since_last_tx: define el label (churned = days > 90)
# - tx_count_30d / tx_count_90d: contadas dentro de la ventana del label
# Solo usamos features de comportamiento histórico estable (pre-corte)
FEATURE_COLS = [
    'tx_count_total',       # volumen histórico total de transacciones
    'tx_count_completed',   # transacciones completadas (calidad)
    'success_rate',         # ratio de éxito (comportamiento de largo plazo)
    'avg_volume_usd',       # ticket promedio histórico
    'total_volume_usd',     # volumen acumulado total
    'volume_trend',         # tendencia de volumen (regresión lineal 8 semanas previas al corte)
    'avg_spread_bps',       # spread promedio pagado
    'spread_vs_minimum',    # margen sobre spread mínimo
    'preferred_hour',       # comportamiento temporal (estable)
    'preferred_day',        # comportamiento temporal (estable)
]


# ── Etiquetado ─────────────────────────────────────────────────────────────────
def build_labels(feat_df, tx_df, reference_date, window=CHURN_WINDOW_DAYS):
    """
    churned = 1 si el cliente tenía actividad antes del corte
              pero ninguna transacción en la ventana final (últimos `window` días).
    churned = 0 si estuvo activo durante la ventana final.
    Clientes sin historial previo suficiente se excluyen.
    """
    cutoff = reference_date - pd.Timedelta(days=window)

    labels = []
    for client_id, group in tx_df.groupby('balance_owner_uuid'):
        g = group.dropna(subset=['trigger_at_dt'])
        past   = g[g['trigger_at_dt'] <  cutoff]
        recent = g[g['trigger_at_dt'] >= cutoff]

        if len(past) < MIN_PAST_TXS:
            continue  # sin historial pasado suficiente

        churned = 1 if len(recent) == 0 else 0
        labels.append({'client_id': client_id, 'churned': churned})

    return pd.DataFrame(labels)


# ── Training ───────────────────────────────────────────────────────────────────
def train(feat_df, labels_df):
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    from sklearn.metrics import (roc_auc_score, classification_report,
                                  average_precision_score)
    try:
        from xgboost import XGBClassifier
        clf = XGBClassifier(
            n_estimators=300,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=1,
            use_label_encoder=False,
            eval_metric='logloss',
            random_state=42,
            verbosity=0,
        )
        model_name = 'XGBoost'
    except ImportError:
        from sklearn.ensemble import GradientBoostingClassifier
        clf = GradientBoostingClassifier(
            n_estimators=200, max_depth=4,
            learning_rate=0.05, subsample=0.8,
            random_state=42,
        )
        model_name = 'GradientBoosting (sklearn fallback — instala xgboost)'

    df = feat_df.merge(labels_df, on='client_id', how='inner')
    df[FEATURE_COLS] = df[FEATURE_COLS].fillna(0)

    X = df[FEATURE_COLS].values
    y = df['churned'].values

    print(f"\nDataset: {len(df)} clientes · Churn rate: {y.mean()*100:.1f}%")
    print(f"Modelo: {model_name}")

    # Cross-val predictions para métricas honestas
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    y_proba_cv = cross_val_predict(clf, X, y, cv=cv, method='predict_proba')[:, 1]

    auc  = roc_auc_score(y, y_proba_cv)
    ap   = average_precision_score(y, y_proba_cv)
    report = classification_report(y, (y_proba_cv > 0.5).astype(int),
                                   target_names=['Activo', 'Churned'])

    print(f"  ROC-AUC (CV-5):  {auc:.3f}")
    print(f"  Avg. Precision:  {ap:.3f}")
    print(report)

    # Entrenar modelo final con todo el dataset
    clf.fit(X, y)

    return clf, df, y_proba_cv, auc, ap, report, model_name


# ── Feature importance ─────────────────────────────────────────────────────────
def feature_importance_text(clf, model_name):
    lines = ["\nFEATURE IMPORTANCE:"]
    if hasattr(clf, 'feature_importances_'):
        importances = clf.feature_importances_
        ranked = sorted(zip(FEATURE_COLS, importances), key=lambda x: -x[1])
        for feat, imp in ranked:
            bar = '█' * int(imp * 40)
            lines.append(f"  {feat:<25} {bar}  {imp:.3f}")
    return '\n'.join(lines)


# ── Score final por cliente ────────────────────────────────────────────────────
def score_all_clients(clf, feat_df):
    """Genera probabilidad de churn para TODOS los clientes en features.parquet."""
    df = feat_df.copy()
    df[FEATURE_COLS] = df[FEATURE_COLS].fillna(0)
    X = df[FEATURE_COLS].values
    proba = clf.predict_proba(X)[:, 1]
    scores = df[['client_id', 'client_name', 'broker_id', 'broker_name', 'segment']].copy()
    scores['churn_probability'] = proba
    scores['churn_score']       = (proba * 100).round(0).astype(int)  # 0–100
    scores['risk_label'] = pd.cut(
        proba,
        bins=[0, 0.3, 0.6, 0.8, 1.0],
        labels=['Bajo', 'Medio', 'Alto', 'Crítico'],
        include_lowest=True,
    )
    return scores.sort_values('churn_probability', ascending=False)


# ── Main ───────────────────────────────────────────────────────────────────────
def run():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. Cargar features
    print("Cargando features.parquet...")
    feat_df = pd.read_parquet(f'{OUTPUT_DIR}/features.parquet')

    # 2. Cargar transacciones para construir etiquetas
    print("Cargando transacciones para etiquetado...")
    raw = pd.read_excel('transactions_anonymized.xlsx')
    trigger_fixed = raw['trigger_at'].astype(str).str.replace(r'\+00$', '+00:00', regex=True)
    raw['trigger_at_dt'] = pd.to_datetime(trigger_fixed, format='mixed', utc=True, errors='coerce')
    reference_date = raw['trigger_at_dt'].dropna().max()
    print(f"  Fecha de referencia: {reference_date.date()}")

    # 3. Construir etiquetas
    print("Construyendo etiquetas de churn...")
    labels_df = build_labels(feat_df, raw, reference_date)
    print(f"  Clientes etiquetados: {len(labels_df):,}")
    print(f"  Churned:  {labels_df['churned'].sum():,} ({labels_df['churned'].mean()*100:.1f}%)")
    print(f"  Activos:  {(labels_df['churned']==0).sum():,}")

    # 4. Entrenar
    clf, df_train, y_proba_cv, auc, ap, report, model_name = train(feat_df, labels_df)

    # 5. Guardar modelo
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump({'model': clf, 'features': FEATURE_COLS, 'model_name': model_name}, f)
    print(f"\nModelo guardado: {MODEL_PATH}")

    # 6. Score de todos los clientes
    scores = score_all_clients(clf, feat_df)
    scores.to_parquet(SCORES_PATH, index=False)
    print(f"Scores guardados: {SCORES_PATH} ({len(scores):,} clientes)")

    # 7. Reporte
    fi_text = feature_importance_text(clf, model_name)
    report_text = f"""EFEX AI — Reporte Modelo de Churn
========================================
Modelo: {model_name}
Fecha:  {reference_date.date()}
Ventana de churn: {CHURN_WINDOW_DAYS} días

DATASET
  Clientes totales:  {len(feat_df):,}
  Clientes con label:{len(labels_df):,}
  Churn rate:        {labels_df['churned'].mean()*100:.1f}%

MÉTRICAS (Cross-validation 5-fold)
  ROC-AUC:           {auc:.3f}
  Avg. Precision:    {ap:.3f}

CLASSIFICATION REPORT
{report}
{fi_text}

DISTRIBUCIÓN DE RIESGO (todos los clientes)
{scores['risk_label'].value_counts().to_string()}
"""
    with open(REPORT_PATH, 'w') as f:
        f.write(report_text)
    print(f"Reporte guardado: {REPORT_PATH}")

    print("\n=== TOP 10 clientes con mayor riesgo de churn ===")
    top10 = scores.head(10)[['client_name', 'broker_name', 'churn_score', 'risk_label', 'segment']]
    print(top10.to_string(index=False))

    return scores


if __name__ == '__main__':
    run()

"""
Feature Engineering + RFM Scoring y Segmentación
Run: python features.py
Genera outputs/features.parquet

Diseño: usa TODAS las transacciones (176k) para features de actividad
(recencia, frecuencia, timing) y solo las COMPLETED con volumen válido
para features monetarios (volumen, spread).
Clientes sin broker asignado reciben broker_id = 'DIRECTO'.
"""
import pandas as pd
import numpy as np
from scipy import stats
import os
import warnings
warnings.filterwarnings('ignore')


def load_all_data():
    """Carga todas las transacciones sin filtrar por status ni broker."""
    print("Cargando datos...")
    df = pd.read_excel('transactions_anonymized.xlsx')

    # Volumen y spread (solo tiene sentido en transacciones con datos numéricos)
    df['bp_num'] = pd.to_numeric(df['balance_paid'], errors='coerce')
    df['volume_usd'] = df['bp_num'] * df['er_paid_to_usd'] / 1e8
    df['spread_bps'] = df['profit_spread_bps'] / 1e8

    # Datetime: fix "+00" → "+00:00" y usar format='mixed' para microsegundos
    trigger_fixed = df['trigger_at'].astype(str).str.replace(r'\+00$', '+00:00', regex=True)
    df['trigger_at_dt'] = pd.to_datetime(trigger_fixed, format='mixed', utc=True, errors='coerce')

    # Broker: string real o None
    df['broker_name_clean'] = df['intermediary_name'].apply(
        lambda x: x if isinstance(x, str) and len(x) > 0 else None
    )
    df['broker_id_clean'] = df['intermediary_uuid'].apply(
        lambda x: x if isinstance(x, str) and len(x) > 0 else None
    )
    df['has_broker'] = df['broker_name_clean'].notna()

    # Nombre de cliente limpio
    df['client_name_clean'] = df['balance_owner_name'].apply(
        lambda x: x if isinstance(x, str) and len(x) > 0 else None
    )

    # Transacciones COMPLETED con volumen válido → para métricas monetarias
    df['is_valid_completed'] = (
        (df['status'] == 'COMPLETED') &
        df['volume_usd'].notna() &
        (df['volume_usd'] > 0) &
        df['trigger_at_dt'].notna()
    )

    print(f"  Total transacciones:          {len(df):>8,}")
    print(f"  Con fecha válida:             {df['trigger_at_dt'].notna().sum():>8,}")
    print(f"  COMPLETED con vol>0:          {df['is_valid_completed'].sum():>8,}")
    print(f"  Con broker asignado:          {df['has_broker'].sum():>8,}")
    print(f"  Clientes únicos totales:      {df['balance_owner_uuid'].nunique():>8,}")
    return df


def compute_volume_trend(group, reference_date):
    """Slope de volumen semanal en las últimas 8 semanas (positivo = creciendo)."""
    cutoff = reference_date - pd.Timedelta(weeks=8)
    recent = group[group['trigger_at_dt'] >= cutoff].copy()
    if len(recent) < 2:
        return 0.0
    recent = recent.copy()
    recent['week_num'] = (
        (recent['trigger_at_dt'] - cutoff).dt.total_seconds() / (7 * 86400)
    ).astype(int)
    weekly = recent.groupby('week_num')['volume_usd'].sum()
    if len(weekly) < 2:
        return 0.0
    try:
        slope, *_ = stats.linregress(weekly.index.values, weekly.values)
        return float(slope)
    except Exception:
        return 0.0


def build_features(df):
    # Fecha de referencia = max fecha con dato válido
    reference_date = df['trigger_at_dt'].dropna().max()
    print(f"\n  Fecha de referencia: {reference_date.date()}")

    now_30 = reference_date - pd.Timedelta(days=30)
    now_90 = reference_date - pd.Timedelta(days=90)

    features = []
    clients = df.groupby('balance_owner_uuid')
    print(f"  Calculando features para {len(clients)} clientes...")

    for client_id, group in clients:
        group = group.sort_values('trigger_at_dt')

        # ── Actividad: usa TODAS las transacciones con fecha válida ──
        g_all = group[group['trigger_at_dt'].notna()]
        if len(g_all) == 0:
            continue  # cliente sin ninguna fecha válida, no procesable

        last_tx = g_all['trigger_at_dt'].max()
        days_since = (reference_date - last_tx).total_seconds() / 86400

        tx_count_total = len(g_all)
        tx_30 = len(g_all[g_all['trigger_at_dt'] >= now_30])
        tx_90 = len(g_all[g_all['trigger_at_dt'] >= now_90])

        hours = g_all['trigger_at_dt'].dt.hour
        days_of_week = g_all['trigger_at_dt'].dt.dayofweek
        preferred_hour = int(hours.mode().iloc[0]) if len(hours) > 0 else 12
        preferred_day = int(days_of_week.mode().iloc[0]) if len(days_of_week) > 0 else 1

        # ── Monetario: solo transacciones COMPLETED con volumen válido ──
        g_mon = group[group['is_valid_completed']]
        avg_vol = g_mon['volume_usd'].mean() if len(g_mon) > 0 else 0.0
        total_vol = g_mon['volume_usd'].sum() if len(g_mon) > 0 else 0.0
        avg_spread = g_mon['spread_bps'].mean() if len(g_mon) > 0 else 0.0
        avg_min_spread = g_mon['minimum_spread'].mean() if len(g_mon) > 0 else 0.0
        spread_vs_min = avg_spread - avg_min_spread

        # Tendencia de volumen solo sobre completed
        trend = compute_volume_trend(g_mon, reference_date) if len(g_mon) >= 2 else 0.0

        # ── Broker: el más frecuente en todas las transacciones ──
        broker_series = group['broker_id_clean'].dropna()
        if len(broker_series) > 0:
            broker_id = broker_series.mode().iloc[0]
            broker_name_s = group[group['broker_id_clean'] == broker_id]['broker_name_clean'].dropna()
            broker_name = str(broker_name_s.iloc[0]) if len(broker_name_s) > 0 else broker_id
        else:
            broker_id = 'DIRECTO'
            broker_name = 'DIRECTO'

        # Nombre del cliente
        client_name_s = group['client_name_clean'].dropna()
        client_name = str(client_name_s.iloc[0]) if len(client_name_s) > 0 else client_id[:8]

        # Tasa de éxito (completed / total)
        success_rate = len(g_mon) / tx_count_total if tx_count_total > 0 else 0.0

        features.append({
            'client_id': client_id,
            'client_name': client_name,
            'days_since_last_tx': days_since,
            'tx_count_total': tx_count_total,
            'tx_count_30d': tx_30,
            'tx_count_90d': tx_90,
            'tx_count_completed': len(g_mon),
            'success_rate': success_rate,
            'avg_volume_usd': avg_vol,
            'total_volume_usd': total_vol,
            'volume_trend': trend,
            'avg_spread_bps': avg_spread,
            'spread_vs_minimum': spread_vs_min,
            'preferred_hour': preferred_hour,
            'preferred_day': preferred_day,
            'broker_id': str(broker_id),
            'broker_name': str(broker_name),
        })

    feat_df = pd.DataFrame(features)
    print(f"  Features calculados para {len(feat_df):,} clientes")
    print(f"  Con broker real:   {(feat_df['broker_id'] != 'DIRECTO').sum():,}")
    print(f"  Clientes DIRECTO:  {(feat_df['broker_id'] == 'DIRECTO').sum():,}")
    return feat_df


def _qscore(series, ascending=True, n=4):
    """Rank a series into n buckets (1..n) using percentiles, handling ties/duplicates."""
    try:
        ranked = pd.qcut(series, q=n, labels=False, duplicates='drop')
        ranked = ranked + 1  # shift to 1-based
        ranked = ranked.fillna(2).astype(int).clip(1, n)
    except Exception:
        ranked = pd.Series([2] * len(series), index=series.index)
    if not ascending:
        ranked = (n + 1) - ranked
    return ranked


def add_rfm(feat_df):
    # R: Recency — menos días = mejor = score más alto
    feat_df['R'] = _qscore(feat_df['days_since_last_tx'], ascending=False)

    # F: Frequency — más transacciones en 90d = mejor
    feat_df['F'] = _qscore(feat_df['tx_count_90d'], ascending=True)

    # M: Monetary — más volumen = mejor
    feat_df['M'] = _qscore(feat_df['total_volume_usd'], ascending=True)

    feat_df['rfm_score'] = feat_df['R'] + feat_df['F'] + feat_df['M']

    def classify(row):
        d = row['days_since_last_tx']
        s = row['rfm_score']
        if s >= 9:
            return 'activo_sano'
        elif s >= 6:
            # Good frequency/monetary but varying recency
            return 'en_riesgo' if d > 45 else 'activo_sano'
        elif d > 180:
            return 'perdido'
        elif d > 30:
            return 'reactivar'
        else:
            # Recent but low RFM = low-activity client, still manageable
            return 'en_riesgo'

    feat_df['segment'] = feat_df.apply(classify, axis=1)

    print("\nDistribución de segmentos:")
    print(feat_df['segment'].value_counts().to_string())
    return feat_df


if __name__ == '__main__':
    os.makedirs('outputs', exist_ok=True)
    df = load_all_data()
    feat_df = build_features(df)
    feat_df = add_rfm(feat_df)
    feat_df.to_parquet('outputs/features.parquet', index=False)
    print(f"\nGuardado: outputs/features.parquet ({len(feat_df):,} clientes)")

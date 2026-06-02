"""
Motor de Oportunidades — detecta CHURN_RISK, REACTIVATION, UPSELL, BEST_TIME por broker
Run: python opportunities.py
Genera outputs/opportunities.parquet
"""
import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings('ignore')

DAYS_OF_WEEK = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

def load_features():
    path = 'outputs/features.parquet'
    if not os.path.exists(path):
        print("features.parquet no encontrado. Ejecutando features.py...")
        import features
        features_df = features.build_features(features.load_all_data())
        features_df = features.add_rfm(features_df)
        os.makedirs('outputs', exist_ok=True)
        features_df.to_parquet(path, index=False)
        return features_df
    return pd.read_parquet(path)

def build_context(row):
    day_name = DAYS_OF_WEEK[row['preferred_day']] if row['preferred_day'] < 7 else 'N/A'
    trend_label = 'creciendo' if row['volume_trend'] > 0 else ('cayendo' if row['volume_trend'] < 0 else 'estable')
    return (
        f"Segmento: {row['segment']} | "
        f"Último tx: hace {row['days_since_last_tx']:.0f} días | "
        f"Volumen total: ${row['total_volume_usd']:,.0f} USD | "
        f"Volumen promedio: ${row['avg_volume_usd']:,.0f} USD | "
        f"Tendencia: {trend_label} | "
        f"Mejor hora: {row['preferred_hour']}:00 {day_name} | "
        f"Spread promedio: {row['avg_spread_bps']:.2f} bps"
    )

def assign_priority(row, opp_type):
    if opp_type == 'CHURN_RISK':
        return 'high' if row['total_volume_usd'] > row.get('vol_p75', 20000) else 'medium'
    elif opp_type == 'REACTIVATION':
        return 'medium' if row['total_volume_usd'] > row.get('vol_p50', 5000) else 'low'
    elif opp_type == 'UPSELL':
        return 'high' if row['volume_trend'] > 0 and row['tx_count_90d'] >= 5 else 'medium'
    else:
        return 'low'

def detect_opportunities(feat_df):
    opportunities = []
    vol_p50 = feat_df['total_volume_usd'].quantile(0.5)
    vol_p75 = feat_df['total_volume_usd'].quantile(0.75)

    for broker_id, broker_group in feat_df.groupby('broker_id'):
        broker_name = broker_group['broker_name'].iloc[0]

        # 1. CHURN_RISK: en_riesgo sorted by volume desc
        churn = broker_group[broker_group['segment'] == 'en_riesgo'].sort_values('total_volume_usd', ascending=False)
        for _, row in churn.iterrows():
            opportunities.append({
                'broker_id': broker_id,
                'broker_name': broker_name,
                'client_id': row['client_id'],
                'client_name': row['client_name'],
                'opportunity_type': 'CHURN_RISK',
                'priority': 'high' if row['total_volume_usd'] > vol_p75 else 'medium',
                'days_since_last_tx': row['days_since_last_tx'],
                'total_volume_usd': row['total_volume_usd'],
                'avg_volume_usd': row['avg_volume_usd'],
                'volume_trend': row['volume_trend'],
                'segment': row['segment'],
                'preferred_hour': row['preferred_hour'],
                'preferred_day': row['preferred_day'],
                'context': build_context(row),
            })

        # 2. REACTIVATION: reactivar with volume > p50
        react = broker_group[
            (broker_group['segment'] == 'reactivar') &
            (broker_group['total_volume_usd'] > vol_p50)
        ].sort_values('total_volume_usd', ascending=False)
        for _, row in react.iterrows():
            opportunities.append({
                'broker_id': broker_id,
                'broker_name': broker_name,
                'client_id': row['client_id'],
                'client_name': row['client_name'],
                'opportunity_type': 'REACTIVATION',
                'priority': 'medium',
                'days_since_last_tx': row['days_since_last_tx'],
                'total_volume_usd': row['total_volume_usd'],
                'avg_volume_usd': row['avg_volume_usd'],
                'volume_trend': row['volume_trend'],
                'segment': row['segment'],
                'preferred_hour': row['preferred_hour'],
                'preferred_day': row['preferred_day'],
                'context': build_context(row),
            })

        # 3. UPSELL: activo_sano con tendencia positiva O alta frecuencia reciente
        upsell = broker_group[
            (broker_group['segment'] == 'activo_sano') &
            (
                (broker_group['volume_trend'] > 0) |
                (broker_group['tx_count_90d'] >= 5)
            )
        ].sort_values('total_volume_usd', ascending=False)
        for _, row in upsell.iterrows():
            opportunities.append({
                'broker_id': broker_id,
                'broker_name': broker_name,
                'client_id': row['client_id'],
                'client_name': row['client_name'],
                'opportunity_type': 'UPSELL',
                'priority': 'high' if row['volume_trend'] > 0 and row['spread_vs_minimum'] > 20 else 'medium',
                'days_since_last_tx': row['days_since_last_tx'],
                'total_volume_usd': row['total_volume_usd'],
                'avg_volume_usd': row['avg_volume_usd'],
                'volume_trend': row['volume_trend'],
                'segment': row['segment'],
                'preferred_hour': row['preferred_hour'],
                'preferred_day': row['preferred_day'],
                'context': build_context(row),
            })

        # 4. BEST_TIME: all active clients (activo_sano + en_riesgo) with preferred contact time
        active = broker_group[broker_group['segment'].isin(['activo_sano', 'en_riesgo'])]
        for _, row in active.iterrows():
            opportunities.append({
                'broker_id': broker_id,
                'broker_name': broker_name,
                'client_id': row['client_id'],
                'client_name': row['client_name'],
                'opportunity_type': 'BEST_TIME',
                'priority': 'low',
                'days_since_last_tx': row['days_since_last_tx'],
                'total_volume_usd': row['total_volume_usd'],
                'avg_volume_usd': row['avg_volume_usd'],
                'volume_trend': row['volume_trend'],
                'segment': row['segment'],
                'preferred_hour': row['preferred_hour'],
                'preferred_day': row['preferred_day'],
                'context': build_context(row),
            })

    opp_df = pd.DataFrame(opportunities)
    print(f"\nOportunidades generadas: {len(opp_df):,}")
    print(opp_df['opportunity_type'].value_counts().to_string())
    return opp_df

if __name__ == '__main__':
    os.makedirs('outputs', exist_ok=True)
    feat_df = load_features()
    opp_df = detect_opportunities(feat_df)
    opp_df.to_parquet('outputs/opportunities.parquet', index=False)
    print(f"\nGuardado: outputs/opportunities.parquet")
    print("\nMuestra de oportunidades:")
    print(opp_df[['broker_name','client_name','opportunity_type','priority','days_since_last_tx','total_volume_usd']].head(10).to_string())

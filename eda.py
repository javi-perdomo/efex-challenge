"""
EDA - Exploratory Data Analysis
Run: python eda.py
Generates summary stats and 4 plots to outputs/eda/
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import warnings
warnings.filterwarnings('ignore')

OUTPUT_DIR = 'outputs/eda'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_data():
    print("Loading data...")
    df = pd.read_excel('transactions_anonymized.xlsx')
    # Parse numeric volume
    df['bp_num'] = pd.to_numeric(df['balance_paid'], errors='coerce')
    df['volume_usd'] = df['bp_num'] * df['er_paid_to_usd'] / 1e8
    df['spread_bps'] = df['profit_spread_bps'] / 1e8
    # Parse datetime
    trigger_fixed = df['trigger_at'].astype(str).str.replace(r'\+00$', '+00:00', regex=True)
    df['trigger_at_dt'] = pd.to_datetime(trigger_fixed, format='mixed', utc=True, errors='coerce')
    # has_broker: rows where intermediary_name is a real string
    df['has_broker'] = df['intermediary_name'].apply(lambda x: isinstance(x, str) and len(x) > 0)
    return df

def run_eda(df):
    print("\n" + "="*60)
    print("EFEX DATASET — EDA REPORT")
    print("="*60)

    print(f"\n1. DIMENSIONES: {df.shape[0]:,} filas x {df.shape[1]} columnas")

    print("\n2. TIPOS Y % NULOS (top columnas relevantes):")
    cols = ['balance_owner_uuid','balance_owner_name','intermediary_uuid','intermediary_name',
            'trigger_at','status','volume_usd','spread_bps','minimum_spread','profit_spread_bps']
    for c in cols:
        if c in df.columns:
            null_pct = df[c].isna().mean() * 100
            print(f"   {c:<40} {str(df[c].dtype):<15} {null_pct:.1f}% nulos")

    # Date range
    print(f"\n3. RANGO DE FECHAS:")
    print(f"   Min trigger_at: {df['trigger_at_dt'].min()}")
    print(f"   Max trigger_at: {df['trigger_at_dt'].max()}")

    # Unique brokers/clients
    with_broker = df[df['has_broker'] & (df['status'] == 'COMPLETED')]
    print(f"\n4. UNIVERSO TRANSACCIONAL (completadas con broker):")
    print(f"   Brokers únicos:  {with_broker['intermediary_uuid'].nunique()}")
    print(f"   Clientes únicos: {with_broker['balance_owner_uuid'].nunique()}")
    print(f"   Transacciones:   {len(with_broker):,}")

    # Volume distribution
    valid_vol = with_broker[with_broker['volume_usd'] > 0]['volume_usd']
    print(f"\n5. DISTRIBUCIÓN balance_paid_usd (USD real):")
    for p in [25, 50, 75, 95, 99]:
        print(f"   p{p}: ${np.percentile(valid_vol, p):>12,.2f}")

    # Top 10 brokers by revenue (use total volume as proxy since revenue cols are corrupt)
    broker_rev = (with_broker[with_broker['volume_usd'] > 0]
                  .groupby(['intermediary_uuid','intermediary_name'])
                  .agg(total_volume_usd=('volume_usd','sum'),
                       tx_count=('volume_usd','count'))
                  .reset_index()
                  .sort_values('total_volume_usd', ascending=False))
    print(f"\n6. TOP 10 BROKERS POR VOLUMEN TOTAL:")
    for _, r in broker_rev.head(10).iterrows():
        print(f"   {r['intermediary_name']:<25} ${r['total_volume_usd']:>15,.0f}  ({r['tx_count']} txs)")

    # Top 10 by unique clients
    broker_clients = (with_broker.groupby(['intermediary_uuid','intermediary_name'])['balance_owner_uuid']
                      .nunique().reset_index()
                      .rename(columns={'balance_owner_uuid':'n_clients'})
                      .sort_values('n_clients', ascending=False))
    print(f"\n7. TOP 10 BROKERS POR CLIENTES ÚNICOS:")
    for _, r in broker_clients.head(10).iterrows():
        print(f"   {r['intermediary_name']:<25} {r['n_clients']} clientes")

    # Status distribution
    print(f"\n8. DISTRIBUCIÓN DE STATUS:")
    status_counts = df['status'].value_counts()
    for s, c in status_counts.items():
        print(f"   {s:<30} {c:>7,} ({c/len(df)*100:.1f}%)")

    return with_broker, broker_rev, broker_clients, valid_vol

def plot_charts(df, with_broker, broker_rev, broker_clients, valid_vol):
    plt.style.use('seaborn-v0_8-whitegrid')
    fig_kwargs = dict(figsize=(10, 6), dpi=120)

    # Plot 1: Volume distribution (log scale)
    fig, ax = plt.subplots(**fig_kwargs)
    ax.hist(np.log10(valid_vol.clip(1)), bins=50, color='#2196F3', edgecolor='white', alpha=0.85)
    ax.set_xlabel('log10(Volumen USD)', fontsize=12)
    ax.set_ylabel('Frecuencia', fontsize=12)
    ax.set_title('Distribución de Volumen por Transacción (USD)', fontsize=14, fontweight='bold')
    ax.set_xticklabels([f'$10^{{{int(x)}}}' for x in ax.get_xticks()])
    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/distribucion_volumen.png')
    plt.close()
    print(f"\nGuardado: {OUTPUT_DIR}/distribucion_volumen.png")

    # Plot 2: Top brokers by volume
    fig, ax = plt.subplots(**fig_kwargs)
    top = broker_rev.head(10).iloc[::-1]
    bars = ax.barh(top['intermediary_name'], top['total_volume_usd'] / 1e6, color='#4CAF50', alpha=0.85)
    ax.set_xlabel('Volumen Total (millones USD)', fontsize=12)
    ax.set_title('Top 10 Brokers por Volumen Total', fontsize=14, fontweight='bold')
    for bar, val in zip(bars, top['total_volume_usd'] / 1e6):
        ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                f'${val:.1f}M', va='center', fontsize=9)
    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/top_brokers_revenue.png')
    plt.close()
    print(f"Guardado: {OUTPUT_DIR}/top_brokers_revenue.png")

    # Plot 3: Status distribution
    fig, ax = plt.subplots(**fig_kwargs)
    status_counts = df['status'].value_counts()
    colors = ['#4CAF50', '#2196F3', '#FF9800', '#F44336', '#9C27B0', '#607D8B']
    ax.pie(status_counts.values, labels=status_counts.index, autopct='%1.1f%%',
           colors=colors[:len(status_counts)], startangle=90)
    ax.set_title('Distribución de Status de Transacciones', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/distribucion_status.png')
    plt.close()
    print(f"Guardado: {OUTPUT_DIR}/distribucion_status.png")

    # Plot 4: Clients per broker
    fig, ax = plt.subplots(**fig_kwargs)
    top_c = broker_clients.head(10).iloc[::-1]
    ax.barh(top_c['intermediary_name'], top_c['n_clients'], color='#FF9800', alpha=0.85)
    ax.set_xlabel('Número de Clientes Únicos', fontsize=12)
    ax.set_title('Top 10 Brokers por Clientes Únicos', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/clientes_por_broker.png')
    plt.close()
    print(f"Guardado: {OUTPUT_DIR}/clientes_por_broker.png")

if __name__ == '__main__':
    df = load_data()
    with_broker, broker_rev, broker_clients, valid_vol = run_eda(df)
    plot_charts(df, with_broker, broker_rev, broker_clients, valid_vol)
    print("\nEDA completado.")

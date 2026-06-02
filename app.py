"""
EFEX AI — Streamlit Dashboard
Run: streamlit run app.py
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import json
import os
import warnings
warnings.filterwarnings('ignore')

os.chdir(os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(
    page_title="EFEX AI",
    page_icon="💱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Design tokens ────────────────────────────────────────────────────────────────
C = {
    'navy':    '#1E3A5F',
    'blue':    '#1E40AF',
    'blue_lt': '#DBEAFE',
    'green':   '#16A34A',
    'green_lt':'#DCFCE7',
    'amber':   '#D97706',
    'amber_lt':'#FEF3C7',
    'red':     '#DC2626',
    'red_lt':  '#FEE2E2',
    'gray':    '#64748B',
    'gray_lt': '#F1F5F9',
    'white':   '#FFFFFF',
    'bg':      '#F8FAFC',
    'border':  '#E2E8F0',
    'text':    '#0F172A',
    'text_sm': '#475569',
}

SEGMENT_COLORS = {
    'activo_sano': C['green'],
    'en_riesgo':   C['amber'],
    'reactivar':   C['blue'],
    'perdido':     C['red'],
}
SEGMENT_LABELS = {
    'activo_sano': 'Cliente Activo',
    'en_riesgo':   'En Riesgo de Irse',
    'reactivar':   'Dormido — Recuperable',
    'perdido':     'Sin Actividad Reciente',
}
OPP_META = {
    'CHURN_RISK':   {'label': 'Riesgo de Pérdida',   'icon': '🚨', 'color': C['red'],   'bg': C['red_lt']},
    'REACTIVATION': {'label': 'Recuperar Cliente',   'icon': '💤', 'color': C['blue'],  'bg': C['blue_lt']},
    'UPSELL':       {'label': 'Crecer Cuenta',        'icon': '📈', 'color': C['green'], 'bg': C['green_lt']},
    'BEST_TIME':    {'label': 'Ventana de Contacto', 'icon': '🎯', 'color': C['gray'],  'bg': C['gray_lt']},
}
PRIORITY_META = {
    'high':   {'label': 'Alta',  'color': C['red'],   'bg': C['red_lt'],   'dot': '🔴'},
    'medium': {'label': 'Media', 'color': C['amber'],  'bg': C['amber_lt'], 'dot': '🟡'},
    'low':    {'label': 'Baja',  'color': C['green'], 'bg': C['green_lt'], 'dot': '🟢'},
}
DAYS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

# ── Global CSS ───────────────────────────────────────────────────────────────────
st.html(f"""<style>
/* Base */
html, body, [class*="css"] {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}}
.main .block-container {{
    padding: 1.5rem 2rem 2rem;
    max-width: 1400px;
}}

/* Hide Streamlit chrome */
#MainMenu, footer, header {{ visibility: hidden; }}
.stDeployButton {{ display: none; }}
/* Keep sidebar toggle visible when sidebar is collapsed */
[data-testid="collapsedControl"] {{ visibility: visible; }}
[data-testid="stExpandSidebarButton"] {{ visibility: visible !important; }}

/* Sidebar */
section[data-testid="stSidebar"] {{
    background: {C['navy']};
    border-right: none;
}}
section[data-testid="stSidebar"] * {{
    color: white !important;
}}
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stMultiSelect label {{
    color: rgba(255,255,255,0.7) !important;
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 600;
}}
section[data-testid="stSidebar"] [data-baseweb="select"] > div {{
    background: rgba(255,255,255,0.1) !important;
    border-color: rgba(255,255,255,0.2) !important;
    color: white !important;
    border-radius: 8px !important;
}}
section[data-testid="stSidebar"] [data-baseweb="select"] span {{
    color: white !important;
}}
section[data-testid="stSidebar"] .stButton > button {{
    background: {C['blue']} !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    padding: 0.6rem 1rem !important;
    width: 100% !important;
    transition: all 0.2s !important;
}}
section[data-testid="stSidebar"] .stButton > button:hover {{
    background: #1D4ED8 !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(30,64,175,0.4) !important;
}}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {{
    background: {C['gray_lt']};
    border-radius: 12px;
    padding: 4px;
    gap: 2px;
    border: 1px solid {C['border']};
}}
.stTabs [data-baseweb="tab"] {{
    border-radius: 9px;
    padding: 0.5rem 1.2rem;
    font-weight: 500;
    font-size: 0.9rem;
    color: {C['text_sm']};
    background: transparent;
    border: none;
}}
.stTabs [aria-selected="true"] {{
    background: {C['white']} !important;
    color: {C['blue']} !important;
    font-weight: 600 !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.1);
}}
.stTabs [data-baseweb="tab-highlight"] {{ display: none; }}
.stTabs [data-baseweb="tab-border"] {{ display: none; }}

/* Metric cards */
div[data-testid="metric-container"] {{
    background: {C['white']};
    border: 1px solid {C['border']};
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}}
div[data-testid="stMetricLabel"] {{
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: {C['text_sm']} !important;
}}
div[data-testid="stMetricValue"] {{
    font-size: 2rem !important;
    font-weight: 700 !important;
    color: {C['text']} !important;
    line-height: 1.1 !important;
}}
div[data-testid="stMetricDelta"] {{
    font-size: 0.8rem !important;
}}

/* Dataframe */
.stDataFrame {{
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid {C['border']};
}}

/* Expander */
.streamlit-expanderHeader {{
    background: {C['gray_lt']} !important;
    border-radius: 10px !important;
    font-weight: 500 !important;
    color: {C['text']} !important;
}}
.streamlit-expanderContent {{
    border: 1px solid {C['border']} !important;
    border-top: none !important;
    border-radius: 0 0 10px 10px !important;
}}

/* Section divider */
hr {{ border: none; border-top: 1px solid {C['border']}; margin: 1.2rem 0; }}

/* Info/warning/error */
div[data-testid="stAlert"] {{
    border-radius: 10px !important;
    border-left-width: 4px !important;
}}
</style>
""")


# ── HTML helpers ─────────────────────────────────────────────────────────────────
def kpi_card(icon, label, value, sub=None, accent=C['blue']):
    sub_html = f'<div style="font-size:0.78rem;color:{C["text_sm"]};margin-top:4px">{sub}</div>' if sub else ''
    return f"""
    <div style="background:{C['white']};border:1px solid {C['border']};border-left:4px solid {accent};
                border-radius:14px;padding:1.2rem 1.4rem;box-shadow:0 1px 3px rgba(0,0,0,0.05);">
        <div style="font-size:0.75rem;font-weight:600;text-transform:uppercase;
                    letter-spacing:0.06em;color:{C['text_sm']};margin-bottom:0.4rem">{icon} {label}</div>
        <div style="font-size:1.9rem;font-weight:700;color:{C['text']};line-height:1.1">{value}</div>
        {sub_html}
    </div>"""

def badge(text, color, bg):
    return f'<span style="display:inline-block;padding:2px 10px;border-radius:20px;font-size:0.75rem;font-weight:600;color:{color};background:{bg};border:1px solid {color}30">{text}</span>'

def section_header(title, subtitle=None):
    sub = f'<p style="margin:0;color:{C["text_sm"]};font-size:0.85rem">{subtitle}</p>' if subtitle else ''
    st.markdown(f"""
    <div style="margin:1.5rem 0 1rem">
        <h3 style="margin:0;font-size:1.1rem;font-weight:700;color:{C['text']}">{title}</h3>
        {sub}
    </div>""", unsafe_allow_html=True)


# ── Ollama not available dialog ───────────────────────────────────────────────────
@st.dialog("⚠️ Ollama no disponible")
def show_ollama_dialog():
    st.markdown(f"""
    <div style="padding:0.5rem 0">
        <p style="font-size:1rem;color:{C['text']};margin-bottom:1rem">
            No se encontró ningún modelo de IA disponible en Ollama.
            Los mensajes se generarán usando <strong>templates predefinidos</strong>.
        </p>
        <p style="font-size:0.9rem;color:{C['text_sm']};margin-bottom:0.3rem">
            Para activar la generación con IA, sigue estos pasos en la terminal:
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.code("brew install ollama", language="bash")
    st.code("ollama serve", language="bash")
    st.code("ollama pull llama3.2", language="bash")

    st.info("Una vez descargado el modelo, recarga la página y vuelve a intentarlo.", icon="💡")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Continuar con templates", type="primary", use_container_width=True):
            st.session_state["gen_with_templates"] = True
            st.rerun()
    with col2:
        if st.button("Cancelar", use_container_width=True):
            st.rerun()


# ── Data loading ─────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Cargando oportunidades...")
def load_opportunities():
    if not os.path.exists('outputs/opportunities.parquet'):
        import features as fm, opportunities as om
        df = fm.load_all_data()
        feat = fm.build_features(df)
        feat = fm.add_rfm(feat)
        os.makedirs('outputs', exist_ok=True)
        feat.to_parquet('outputs/features.parquet', index=False)
        opp = om.detect_opportunities(feat)
        opp.to_parquet('outputs/opportunities.parquet', index=False)
        return opp
    return pd.read_parquet('outputs/opportunities.parquet')

@st.cache_data(show_spinner=False)
def load_features():
    if not os.path.exists('outputs/features.parquet'):
        load_opportunities()
    return pd.read_parquet('outputs/features.parquet')

@st.cache_data(show_spinner=False)
def load_churn_scores():
    path = 'outputs/churn_scores.parquet'
    if os.path.exists(path):
        return pd.read_parquet(path)[['client_id', 'churn_probability', 'churn_score', 'risk_label']]
    return pd.DataFrame(columns=['client_id', 'churn_probability', 'churn_score', 'risk_label'])

@st.cache_data(show_spinner=False)
def load_transactions():
    df = pd.read_excel('transactions_anonymized.xlsx')
    df['bp_num'] = pd.to_numeric(df['balance_paid'], errors='coerce')
    df['volume_usd'] = df['bp_num'] * df['er_paid_to_usd'] / 1e8
    trigger_fixed = df['trigger_at'].astype(str).str.replace(r'\+00$', '+00:00', regex=True)
    df['trigger_at_dt'] = pd.to_datetime(trigger_fixed, format='mixed', utc=True, errors='coerce')
    df['has_broker'] = df['intermediary_name'].apply(lambda x: isinstance(x, str) and len(x) > 0)
    df['month'] = df['trigger_at_dt'].dt.to_period('M').astype(str)
    return df[(df['status'] == 'COMPLETED') & df['volume_usd'].notna() & (df['volume_usd'] > 0)]

def load_messages():
    if os.path.exists('outputs/messages.json'):
        with open('outputs/messages.json') as f:
            return json.load(f)
    return []


# ── Sidebar ───────────────────────────────────────────────────────────────────────
def render_sidebar(opp_df, feat_df):
    with st.sidebar:
        # Logo
        st.markdown(f"""
        <div style="padding:1.5rem 0.5rem 1rem;text-align:center;">
            <div style="font-size:2.2rem;margin-bottom:0.2rem">💱</div>
            <div style="font-size:1.4rem;font-weight:800;letter-spacing:-0.5px">EFEX AI</div>
            <div style="font-size:0.75rem;opacity:0.6;font-weight:500;letter-spacing:0.1em;
                        text-transform:uppercase;margin-top:2px">Broker Copilot</div>
        </div>
        <div style="height:1px;background:rgba(255,255,255,0.15);margin:0 0.5rem 1rem"></div>
        """, unsafe_allow_html=True)

        # Broker selector
        brokers = opp_df[['broker_id','broker_name']].drop_duplicates().sort_values('broker_name')
        broker_opts = {r['broker_name']: r['broker_id'] for _, r in brokers.iterrows()}
        sel_name = st.selectbox("Broker / Promotor", list(broker_opts.keys()), label_visibility="visible")
        sel_id = broker_opts[sel_name]

        # Opp type filter
        opp_types = ['Todas'] + sorted(opp_df['opportunity_type'].unique().tolist())
        sel_opp = st.selectbox("Tipo de oportunidad", opp_types, label_visibility="visible")

        st.markdown('<div style="height:1px;background:rgba(255,255,255,0.15);margin:1rem 0.5rem"></div>', unsafe_allow_html=True)

        gen_btn = st.button("⚡ Generar mensajes con IA", use_container_width=True)

        st.markdown('<div style="height:1px;background:rgba(255,255,255,0.15);margin:1rem 0.5rem"></div>', unsafe_allow_html=True)

        # System status
        st.markdown('<div style="font-size:0.7rem;font-weight:600;opacity:0.5;text-transform:uppercase;letter-spacing:0.08em;padding:0 0.2rem">Estado del sistema</div>', unsafe_allow_html=True)
        try:
            import requests as req
            r = req.get('http://localhost:11434/api/tags', timeout=2)
            models = [m['name'] for m in r.json().get('models', [])] if r.status_code == 200 else []
            if models:
                st.markdown(f'<div style="margin-top:0.5rem;padding:0.5rem 0.7rem;background:rgba(22,163,74,0.25);border-radius:8px;border:1px solid rgba(22,163,74,0.4);font-size:0.8rem">✅ Ollama · {models[0]}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div style="margin-top:0.5rem;padding:0.5rem 0.7rem;background:rgba(217,119,6,0.2);border-radius:8px;font-size:0.8rem">⚠️ Ollama sin modelos</div>', unsafe_allow_html=True)
        except Exception:
            st.markdown('<div style="margin-top:0.5rem;padding:0.5rem 0.7rem;background:rgba(220,38,38,0.2);border-radius:8px;border:1px solid rgba(220,38,38,0.3);font-size:0.8rem">❌ Ollama offline · templates</div>', unsafe_allow_html=True)

        for fname, label in [('features.parquet','Features'), ('opportunities.parquet','Oportunidades'), ('messages.json','Mensajes')]:
            ok = os.path.exists(f'outputs/{fname}')
            st.markdown(f'<div style="font-size:0.78rem;opacity:0.7;padding:0.15rem 0.2rem">{"✅" if ok else "⏳"} {label}</div>', unsafe_allow_html=True)

        st.markdown('<div style="height:1px;background:rgba(255,255,255,0.15);margin:1rem 0.5rem"></div>', unsafe_allow_html=True)

        # Global stats
        st.markdown('<div style="font-size:0.7rem;font-weight:600;opacity:0.5;text-transform:uppercase;letter-spacing:0.08em;padding:0 0.2rem 0.5rem">Resumen global</div>', unsafe_allow_html=True)
        total_brokers = opp_df['broker_id'].nunique()
        total_clients = feat_df['client_id'].nunique()
        n_risk = len(feat_df[feat_df['segment'] == 'en_riesgo'])
        for lbl, val in [("Brokers activos", total_brokers), ("Clientes totales", total_clients), ("En riesgo de irse", n_risk)]:
            st.markdown(f'<div style="display:flex;justify-content:space-between;padding:0.25rem 0.2rem;font-size:0.85rem"><span style="opacity:0.7">{lbl}</span><span style="font-weight:700">{val}</span></div>', unsafe_allow_html=True)

    return sel_id, sel_name, sel_opp, gen_btn


# ── Tab 1: Opportunities ──────────────────────────────────────────────────────────
def render_opportunities_tab(broker_opps, feat_df, broker_id, broker_name, churn_scores=None):
    bf = feat_df[feat_df['broker_id'] == broker_id]

    n_total    = len(bf)
    n_active   = len(bf[bf['segment'] == 'activo_sano'])
    n_risk     = len(bf[bf['segment'] == 'en_riesgo'])
    n_react    = len(bf[bf['segment'] == 'reactivar'])
    n_upsell   = len(broker_opps[broker_opps['opportunity_type'] == 'UPSELL'])
    risk_vol   = bf[bf['segment'] == 'en_riesgo']['total_volume_usd'].sum()
    total_vol  = bf['total_volume_usd'].sum()

    # KPI row
    cols = st.columns(5, gap="small")
    cards = [
        ("👥", "Clientes totales",      str(n_total),   f"${total_vol:,.0f} USD vol. total",      C['blue']),
        ("✅", "Clientes activos",     str(n_active),  f"{round(n_active/n_total*100) if n_total else 0}% del portafolio",  C['green']),
        ("⚠️", "En riesgo de irse",   str(n_risk),    f"${risk_vol:,.0f} en juego",               C['amber']),
        ("💤", "Dormidos — Recuperar", str(n_react),   "Contacto puede reactivarlos",              C['blue']),
        ("📈", "Crecer cuenta",        str(n_upsell),  "Con tendencia de volumen creciente",       C['green']),
    ]
    for col, (icon, lbl, val, sub, color) in zip(cols, cards):
        col.markdown(kpi_card(icon, lbl, val, sub, color), unsafe_allow_html=True)

    st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)

    # Filters row
    col_f1, col_f2, _ = st.columns([2, 2, 4])
    with col_f1:
        prio_filter = st.multiselect(
            "Prioridad",
            options=['high','medium','low'],
            default=['high','medium'],
            format_func=lambda x: f"{PRIORITY_META[x]['dot']} {PRIORITY_META[x]['label']}",
            key="opp_prio_filter"
        )
    with col_f2:
        type_filter = st.multiselect(
            "Tipo",
            options=list(OPP_META.keys()),
            default=[k for k in OPP_META if k != 'BEST_TIME'],
            format_func=lambda x: f"{OPP_META[x]['icon']} {OPP_META[x]['label']}",
            key="opp_type_filter"
        )

    filtered = broker_opps.copy()
    if prio_filter:
        filtered = filtered[filtered['priority'].isin(prio_filter)]
    if type_filter:
        filtered = filtered[filtered['opportunity_type'].isin(type_filter)]

    section_header(f"Oportunidades detectadas", f"{len(filtered)} resultados")

    if len(filtered) == 0:
        st.info("Sin oportunidades con los filtros seleccionados.")
        return

    # Build display table (incluir client_id para merge con churn scores)
    disp = filtered[['client_id','client_name','opportunity_type','priority',
                      'days_since_last_tx','total_volume_usd']].copy().reset_index(drop=True)
    disp['Tipo']      = disp['opportunity_type'].map(lambda x: f"{OPP_META[x]['icon']} {OPP_META[x]['label']}" if x in OPP_META else x)
    disp['Prioridad'] = disp['priority'].map(lambda x: f"{PRIORITY_META[x]['dot']} {PRIORITY_META[x]['label']}" if x in PRIORITY_META else x)
    disp['Inactivo']  = disp['days_since_last_tx'].map(lambda x: f"{x:.0f}d")
    disp = disp.rename(columns={'client_name': 'Cliente'})

    # Merge churn score si existe el modelo
    has_churn = False
    if churn_scores is not None and len(churn_scores) > 0:
        disp = disp.merge(churn_scores[['client_id', 'churn_probability']], on='client_id', how='left')
        disp['churn_probability'] = (disp['churn_probability'] * 100).round(1)
        has_churn = disp['churn_probability'].notna().any()

    cols_to_show = ['Cliente', 'Tipo', 'Prioridad', 'Inactivo', 'total_volume_usd']
    col_cfg = {
        "Cliente":          st.column_config.TextColumn("Cliente"),
        "Tipo":             st.column_config.TextColumn("Tipo"),
        "Prioridad":        st.column_config.TextColumn("Prioridad"),
        "Inactivo":         st.column_config.TextColumn("Días inactivo"),
        "total_volume_usd": st.column_config.NumberColumn("Volumen Total", format="$%,.0f"),
    }
    if has_churn:
        cols_to_show.append('churn_probability')
        col_cfg['churn_probability'] = st.column_config.ProgressColumn(
            "Riesgo Churn 🤖",
            format="%.1f%%",
            min_value=0, max_value=100,
            help="Probabilidad de abandono según modelo XGBoost (ROC-AUC 0.96)",
        )

    st.dataframe(
        disp[cols_to_show],
        use_container_width=True,
        height=min(420, 56 + len(disp) * 35),
        column_config=col_cfg,
        hide_index=True,
    )

    # Mini charts
    st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="medium")

    with c1:
        # Show full distribution of ALL opportunity types (unaffected by table filter)
        if len(broker_opps) > 0:
            counts = broker_opps['opportunity_type'].value_counts().reset_index()
            counts.columns = ['type','n']
            counts['label'] = counts['type'].map(lambda x: OPP_META[x]['label'] if x in OPP_META else x)
            counts['color'] = counts['type'].map(lambda x: OPP_META[x]['color'] if x in OPP_META else C['gray'])
            fig = go.Figure(go.Pie(
                labels=counts['label'], values=counts['n'],
                hole=0.55, marker_colors=counts['color'].tolist(),
                textinfo='percent+label', textfont_size=12,
            ))
            fig.update_layout(
                title=dict(text="Distribución por tipo", font_size=13, x=0.02),
                height=260, margin=dict(t=36,b=0,l=0,r=0),
                showlegend=False,
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        seg_c = bf['segment'].value_counts().reset_index()
        seg_c.columns = ['seg','n']
        seg_c['label'] = seg_c['seg'].map(lambda x: SEGMENT_LABELS.get(x, x))
        seg_c['color'] = seg_c['seg'].map(lambda x: SEGMENT_COLORS.get(x, C['gray']))
        fig2 = go.Figure(go.Bar(
            x=seg_c['n'], y=seg_c['label'], orientation='h',
            marker_color=seg_c['color'].tolist(),
            text=seg_c['n'], textposition='outside',
        ))
        fig2.update_layout(
            title=dict(text="Clientes por segmento RFM", font_size=13, x=0.02),
            height=260, margin=dict(t=36,b=0,l=0,r=40),
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig2, use_container_width=True)


# ── Tab 2: WhatsApp Messages ──────────────────────────────────────────────────────
def render_messages_tab(broker_opps, broker_id, broker_name):
    messages  = load_messages()
    broker_msgs = [m for m in messages if m.get('broker_id') == broker_id]

    # Header
    n_msgs = len(broker_msgs)
    n_ai   = sum(1 for m in broker_msgs if m.get('source') == 'ollama')

    if n_msgs:
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:1rem;
                    padding:1rem 1.2rem;background:{C['white']};border:1px solid {C['border']};
                    border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.05)">
            <div style="width:44px;height:44px;background:{C['green_lt']};border-radius:50%;
                        display:flex;align-items:center;justify-content:center;font-size:1.3rem">💬</div>
            <div>
                <div style="font-weight:700;font-size:1rem;color:{C['text']}">{n_msgs} mensajes para {broker_name}</div>
                <div style="font-size:0.82rem;color:{C['text_sm']}">{n_ai} generados con IA · {n_msgs - n_ai} con templates</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Filters
        c1, c2 = st.columns([2, 2])
        with c1:
            tf = st.multiselect("Tipo", list(OPP_META.keys()), default=list(OPP_META.keys()),
                                format_func=lambda x: f"{OPP_META[x]['icon']} {OPP_META[x]['label']}",
                                key="msg_type_filter")
        with c2:
            pf = st.multiselect("Prioridad", ['high','medium','low'], default=['high','medium'],
                                format_func=lambda x: f"{PRIORITY_META[x]['dot']} {PRIORITY_META[x]['label']}",
                                key="msg_prio_filter")

        show = [m for m in broker_msgs
                if m.get('opportunity_type') in (tf or list(OPP_META.keys()))
                and m.get('priority') in (pf or ['high','medium','low'])]
    else:
        show = []

    if not show:
        # Empty state with preview
        st.markdown(f"""
        <div style="text-align:center;padding:2rem;background:{C['gray_lt']};border-radius:16px;
                    border:2px dashed {C['border']};margin:1rem 0">
            <div style="font-size:2.5rem;margin-bottom:0.5rem">💬</div>
            <div style="font-weight:600;color:{C['text']};margin-bottom:0.3rem">Sin mensajes generados</div>
            <div style="color:{C['text_sm']};font-size:0.87rem">
                Haz clic en <strong>⚡ Generar mensajes con IA</strong> en el panel lateral
            </div>
        </div>
        """, unsafe_allow_html=True)

        preview_rows = broker_opps[broker_opps['opportunity_type'].isin(['CHURN_RISK','REACTIVATION','UPSELL'])].head(2)
        if len(preview_rows) > 0:
            st.markdown(f"<div style='font-size:0.82rem;font-weight:600;color:{C['text_sm']};text-transform:uppercase;letter-spacing:0.06em;margin:1.5rem 0 0.8rem'>Vista previa de templates</div>", unsafe_allow_html=True)
            for _, row in preview_rows.iterrows():
                from message_generator import generate_template
                _render_wa_bubble(generate_template(row), row['opportunity_type'], row['client_name'], broker_name)
        return

    for msg in show:
        _render_wa_bubble(msg['message'], msg['opportunity_type'], msg['client_name'], broker_name,
                          priority=msg.get('priority','medium'), source=msg.get('source','template'),
                          context=msg.get('context',''), client_id=msg.get('client_id',''),
                          broker_id=broker_id)


def _render_wa_bubble(message, opp_type, client_name, broker_name,
                      priority=None, source=None, context=None, client_id=None, broker_id=None):
    meta = OPP_META.get(opp_type, OPP_META['BEST_TIME'])
    prio = PRIORITY_META.get(priority, PRIORITY_META['medium']) if priority else None

    prio_badge = f'<span style="background:{prio["bg"]};color:{prio["color"]};padding:2px 8px;border-radius:20px;font-size:0.7rem;font-weight:600;border:1px solid {prio["color"]}40">{prio["dot"]} {prio["label"]}</span>' if prio else ''
    src_badge  = f'<span style="background:{C["gray_lt"]};color:{C["gray"]};padding:2px 8px;border-radius:20px;font-size:0.7rem;font-weight:600">{"🤖 IA" if source == "ollama" else "📝 Template"}</span>' if source else ''
    expander_label = f"{meta['icon']} {meta['label']} — {client_name}"
    if priority:
        expander_label += f"  ·  {PRIORITY_META.get(priority,{}).get('dot','')} {PRIORITY_META.get(priority,{}).get('label','')}"

    with st.expander(expander_label, expanded=(priority == 'high')):
        # WA UI
        st.markdown(f"""
        <div style="max-width:640px;margin:0 auto 0.5rem;border-radius:16px;
                    overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.12)">
            <!-- Header bar -->
            <div style="background:#075E54;padding:0.7rem 1rem;display:flex;align-items:center;gap:10px">
                <div style="width:38px;height:38px;border-radius:50%;background:#25D366;
                            display:flex;align-items:center;justify-content:center;
                            font-size:1.1rem;flex-shrink:0">💱</div>
                <div>
                    <div style="color:white;font-weight:600;font-size:0.9rem">EFEX AI</div>
                    <div style="color:rgba(255,255,255,0.7);font-size:0.75rem">Para: {broker_name}</div>
                </div>
                <div style="margin-left:auto;display:flex;gap:6px">{prio_badge} {src_badge}</div>
            </div>
            <!-- Chat background -->
            <div style="background:#E5DDD5;padding:1rem 1rem 0.5rem;
                        background-image:url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI0U1RERENSIvPjwvc3ZnPg==')">
                <!-- Bubble -->
                <div style="background:#DCF8C6;border-radius:0 12px 12px 12px;
                            padding:0.8rem 1rem;max-width:90%;
                            box-shadow:0 1px 2px rgba(0,0,0,0.15);
                            font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
                            font-size:0.875rem;line-height:1.55;
                            color:#111827;white-space:pre-wrap">
{message}
                </div>
                <div style="text-align:right;font-size:0.7rem;color:#667781;
                            padding:0.3rem 0.2rem 0.4rem">✓✓ Ahora</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Actions row
        ca, cb, _ = st.columns([2, 2, 4])
        with ca:
            msg_safe = message.replace('\\', '\\\\').replace('`', '\\`').replace('\n', '\\n').replace('"', '\\"')
            st.markdown(f"""
            <button onclick="navigator.clipboard.writeText(`{msg_safe}`).then(()=>{{
                this.innerHTML='✅ Copiado!';
                setTimeout(()=>this.innerHTML='📋 Copiar mensaje',2000)
            }})" style="background:#25D366;color:white;border:none;padding:0.45rem 1rem;
                border-radius:8px;cursor:pointer;font-size:0.83rem;font-weight:500;width:100%">
                📋 Copiar mensaje
            </button>""", unsafe_allow_html=True)
        with cb:
            if context:
                with st.popover("📊 Ver contexto"):
                    st.caption(context)


# ── Tab 3: Broker Analysis ────────────────────────────────────────────────────────
def render_analysis_tab(broker_opps, feat_df, tx_df, broker_id, broker_name, churn_scores=None):
    bf = feat_df[feat_df['broker_id'] == broker_id]
    bt = tx_df[tx_df['intermediary_uuid'] == broker_id] if broker_id != 'DIRECTO' else pd.DataFrame()

    if len(bf) == 0:
        st.info("Sin datos históricos para este broker.")
        return

    # KPIs — use bt if available, fallback to bf aggregates
    total_vol  = bt['volume_usd'].sum()  if len(bt) > 0 else bf['total_volume_usd'].sum()
    avg_vol    = bt['volume_usd'].mean() if len(bt) > 0 else bf['avg_volume_usd'].mean()
    tx_count   = len(bt)                 if len(bt) > 0 else int(bf['tx_count_completed'].sum())
    n_clients  = bf['client_id'].nunique()

    cols = st.columns(4, gap="small")
    kpis = [
        ("💰", "Volumen total",   f"${total_vol/1e6:.1f}M" if total_vol >= 1e6 else f"${total_vol:,.0f}", "USD acumulado",    C['blue']),
        ("📊", "Ticket promedio", f"${avg_vol:,.0f}",       "por transacción",                              C['navy']),
        ("🔄", "Transacciones",   f"{tx_count:,}",           "completadas",                                  C['green']),
        ("👥", "Clientes",        f"{n_clients}",            "en portafolio activo",                         C['amber']),
    ]
    for col, (icon, lbl, val, sub, color) in zip(cols, kpis):
        col.markdown(kpi_card(icon, lbl, val, sub, color), unsafe_allow_html=True)

    st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)

    # ── Row 1: Segmentación RFM (donut) + Top clientes (barras) ──────────────────
    c1, c2 = st.columns([2, 3], gap="medium")

    with c1:
        section_header("Segmentación RFM")
        seg_c = bf['segment'].value_counts().reset_index()
        seg_c.columns = ['seg', 'n']
        seg_c['label'] = seg_c['seg'].map(lambda x: SEGMENT_LABELS.get(x, x))
        seg_c['color'] = seg_c['seg'].map(lambda x: SEGMENT_COLORS.get(x, C['gray']))
        fig_pie = go.Figure(go.Pie(
            labels=seg_c['label'], values=seg_c['n'],
            hole=0.52,
            marker_colors=seg_c['color'].tolist(),
            textinfo='label+percent',
            textfont_size=11,
            insidetextorientation='radial',
        ))
        fig_pie.update_layout(
            height=300, margin=dict(t=10, b=10, l=0, r=0),
            showlegend=False,
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with c2:
        section_header("Top 10 clientes por volumen")
        top10 = bf.nlargest(10, 'total_volume_usd')
        top10 = top10.iloc[::-1]  # reverse so largest is at top
        fig_bar = go.Figure(go.Bar(
            x=top10['total_volume_usd'],
            y=top10['client_name'],
            orientation='h',
            marker_color=[SEGMENT_COLORS.get(s, C['gray']) for s in top10['segment']],
            text=[f"${v:,.0f}" for v in top10['total_volume_usd']],
            textposition='outside',
            textfont_size=11,
            cliponaxis=False,
        ))
        fig_bar.update_layout(
            height=300, margin=dict(t=10, b=10, l=10, r=100),
            xaxis=dict(showgrid=False, showticklabels=False, range=[0, top10['total_volume_usd'].max() * 1.25]),
            yaxis=dict(showgrid=False, tickfont_size=11),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # ── Row 2: Volumen mensual + Heatmap de actividad ─────────────────────────────
    c3, c4 = st.columns([3, 2], gap="medium")

    with c3:
        section_header("Volumen mensual", "Evolución histórica de transacciones completadas")
        if len(bt) > 0:
            monthly = bt.groupby('month')['volume_usd'].sum().reset_index().sort_values('month')
            monthly = monthly[monthly['month'] != 'NaT']
            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(
                x=monthly['month'], y=monthly['volume_usd'],
                mode='lines+markers',
                line=dict(color=C['blue'], width=2.5),
                marker=dict(size=6, color=C['blue']),
                fill='tozeroy',
                fillcolor='rgba(30,64,175,0.08)',
                name='Volumen'
            ))
            fig_line.update_layout(
                height=260, margin=dict(t=10, b=40, l=10, r=10),
                xaxis=dict(showgrid=False, tickangle=45, tickfont_size=10),
                yaxis=dict(showgrid=True, gridcolor='#F1F5F9', tickformat='$,.0f', tickfont_size=10),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                showlegend=False,
            )
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            # Fallback: total_volume_usd por cliente (top 15)
            top15 = bf.nlargest(15, 'total_volume_usd')[['client_name', 'total_volume_usd', 'segment']]
            fig_fb = go.Figure(go.Bar(
                x=top15['client_name'],
                y=top15['total_volume_usd'],
                marker_color=[SEGMENT_COLORS.get(s, C['gray']) for s in top15['segment']],
                text=[f"${v:,.0f}" for v in top15['total_volume_usd']],
                textposition='outside',
                textfont_size=10,
                cliponaxis=False,
            ))
            fig_fb.update_layout(
                height=260, margin=dict(t=10, b=80, l=10, r=10),
                xaxis=dict(showgrid=False, tickangle=45, tickfont_size=10),
                yaxis=dict(showgrid=False, showticklabels=False,
                           range=[0, top15['total_volume_usd'].max() * 1.15]),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            )
            st.plotly_chart(fig_fb, use_container_width=True)

    with c4:
        section_header("Patrón de actividad", "Hora y día con más transacciones")
        if len(bt) > 0:
            btc = bt.dropna(subset=['trigger_at_dt']).copy()
            btc['hour'] = btc['trigger_at_dt'].dt.hour
            btc['dow']  = btc['trigger_at_dt'].dt.dayofweek
            hm = btc.groupby(['dow', 'hour']).size().reset_index(name='n')
            pivot = hm.pivot(index='dow', columns='hour', values='n').fillna(0)
            pivot = pivot.reindex(range(7), fill_value=0).reindex(columns=range(24), fill_value=0)
        else:
            # Fallback: use preferred_day/preferred_hour from features
            import numpy as np
            pivot = pd.DataFrame(0, index=range(7), columns=range(24))
            for _, row in bf.iterrows():
                d, h = int(row['preferred_day']) % 7, int(row['preferred_hour']) % 24
                pivot.loc[d, h] += 1

        fig_hm = go.Figure(go.Heatmap(
            z=pivot.values,
            x=[f"{h:02d}h" for h in range(24)],
            y=['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'],
            colorscale=[[0, '#F0F9FF'], [0.5, '#60A5FA'], [1, '#1E3A5F']],
            showscale=False,
            xgap=2, ygap=2,
            hovertemplate='%{y} %{x}: %{z} transacciones<extra></extra>',
        ))
        fig_hm.update_layout(
            height=260, margin=dict(t=10, b=10, l=40, r=10),
            xaxis=dict(tickfont_size=9, tickvals=list(range(0, 24, 3)),
                       ticktext=[f"{h:02d}h" for h in range(0, 24, 3)]),
            yaxis=dict(tickfont_size=11),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        )
        st.plotly_chart(fig_hm, use_container_width=True)

    # ── Estado de clientes ────────────────────────────────────────────────────────
    section_header("Estado de clientes", "Semáforo de actividad y mejor momento de contacto")

    def semaforo(d):
        if d < 14:  return '🟢 Activo'
        if d <= 30: return '🟡 Atención'
        if d <= 90: return '🟠 Inactivo'
        return '🔴 Sin actividad'

    def trend_icon(t):
        if t > 500:  return '📈 Fuerte alza'
        if t > 0:    return '↗️ Creciendo'
        if t < -500: return '📉 Caída fuerte'
        if t < 0:    return '↘️ Bajando'
        return '➡️ Estable'

    tbl = bf[['client_id', 'client_name', 'segment', 'days_since_last_tx', 'tx_count_30d', 'tx_count_90d',
              'total_volume_usd', 'volume_trend', 'preferred_day', 'preferred_hour']].copy()
    tbl['Estado']    = tbl['days_since_last_tx'].map(semaforo)
    tbl['Tendencia'] = tbl['volume_trend'].map(trend_icon)
    tbl['Mejor contacto'] = tbl.apply(
        lambda r: f"{DAYS[int(r['preferred_day']) % 7]} a las {int(r['preferred_hour']):02d}:00", axis=1)

    # Merge churn scores
    has_churn = churn_scores is not None and len(churn_scores) > 0
    if has_churn:
        tbl = tbl.merge(churn_scores[['client_id', 'churn_probability']], on='client_id', how='left')
        tbl['churn_probability'] = (tbl['churn_probability'] * 100).round(1)

    tbl = tbl.sort_values('days_since_last_tx')
    tbl = tbl.rename(columns={'client_name': 'Cliente', 'segment': 'Segmento'})
    tbl['Días inactivo'] = tbl['days_since_last_tx'].map(lambda x: f"{x:.0f}d")
    tbl['Volumen total'] = tbl['total_volume_usd'].map(lambda x: f"${x:,.0f}")
    tbl['Txs 30d']       = tbl['tx_count_30d'].astype(int)
    tbl['Txs 90d']       = tbl['tx_count_90d'].astype(int)
    tbl['Segmento']      = tbl['Segmento'].map(lambda x: SEGMENT_LABELS.get(x, x))

    display_cols = ['Cliente', 'Estado', 'Segmento', 'Días inactivo', 'Txs 30d', 'Txs 90d',
                    'Volumen total', 'Tendencia', 'Mejor contacto']
    col_cfg = {}
    if has_churn:
        display_cols.append('churn_probability')
        col_cfg['churn_probability'] = st.column_config.ProgressColumn(
            "Riesgo Churn 🤖",
            format="%.1f%%",
            min_value=0, max_value=100,
            help="Probabilidad de abandono según modelo XGBoost (ROC-AUC 0.96)",
        )

    st.dataframe(
        tbl[display_cols],
        column_config=col_cfg if col_cfg else None,
        use_container_width=True,
        height=min(460, 56 + len(tbl) * 35),
        hide_index=True,
    )


# ── Main ──────────────────────────────────────────────────────────────────────────
def main():
    opp_df      = load_opportunities()
    feat_df     = load_features()
    churn_scores = load_churn_scores()

    sel_id, sel_name, sel_opp, gen_btn = render_sidebar(opp_df, feat_df)

    broker_opps_all = opp_df[opp_df['broker_id'] == sel_id]
    n_opps = len(broker_opps_all[broker_opps_all['opportunity_type'] != 'BEST_TIME'])
    n_high = len(broker_opps_all[broker_opps_all['priority'] == 'high'])

    # Page header
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,{C['navy']} 0%,{C['blue']} 100%);
                padding:1.4rem 1.8rem;border-radius:16px;margin-bottom:1.5rem;
                display:flex;align-items:center;justify-content:space-between;
                box-shadow:0 4px 20px rgba(30,58,95,0.25)">
        <div>
            <div style="font-size:0.7rem;color:rgba(255,255,255,0.6);font-weight:600;
                        text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px">EFEX AI</div>
            <div style="font-size:1.5rem;font-weight:800;color:white;line-height:1.1">{sel_name}</div>
        </div>
        <div style="display:flex;gap:10px;align-items:center">
            <div style="background:rgba(255,255,255,0.15);border-radius:10px;padding:0.5rem 1rem;text-align:center">
                <div style="font-size:1.4rem;font-weight:800;color:white">{n_opps}</div>
                <div style="font-size:0.7rem;color:rgba(255,255,255,0.7)">Oportunidades</div>
            </div>
            <div style="background:rgba(220,38,38,0.35);border-radius:10px;padding:0.5rem 1rem;text-align:center;border:1px solid rgba(220,38,38,0.5)">
                <div style="font-size:1.4rem;font-weight:800;color:#FCA5A5">{n_high}</div>
                <div style="font-size:0.7rem;color:rgba(255,255,255,0.7)">Alta prioridad</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Generate messages
    from message_generator import generate_batch, check_ollama

    if gen_btn:
        model = check_ollama()
        if model is None and not st.session_state.get("gen_with_templates"):
            show_ollama_dialog()
        else:
            st.session_state.pop("gen_with_templates", None)
            use_ollama = model is not None

            broker_opps_for_gen = opp_df[opp_df['broker_id'] == sel_id]
            total_msgs = len(broker_opps_for_gen)

            status_box  = st.empty()
            progress_bar = st.progress(0, text="Iniciando generación...")

            def on_progress(current, total, client_name, opp_type, source):
                pct  = current / total
                icon = "🤖" if source == "ollama" else "📝"
                progress_bar.progress(pct, text=f"{icon} [{current}/{total}] {client_name} — {opp_type}")

            results = generate_batch(
                sel_id, opp_df=opp_df,
                use_ollama=use_ollama, model=model, save=True,
                progress_callback=on_progress,
            )

            progress_bar.empty()
            n_ai = sum(1 for r in results if r.get('source') == 'ollama')
            src  = f"Ollama · {model}" if model else "templates"
            status_box.success(f"✅ {len(results)} mensajes generados con {src} · {n_ai} con IA.")
            st.cache_data.clear()
            st.rerun()

    # Filter
    broker_opps = broker_opps_all.copy()
    if sel_opp != 'Todas':
        broker_opps = broker_opps[broker_opps['opportunity_type'] == sel_opp]

    # Tabs
    tab1, tab2, tab3 = st.tabs(["📋  Oportunidades", "💬  Mensajes WhatsApp", "📊  Análisis del Broker"])

    with tab1:
        if len(broker_opps):
            render_opportunities_tab(broker_opps, feat_df, sel_id, sel_name, churn_scores)
        else:
            st.info("Sin oportunidades para el filtro seleccionado.")

    with tab2:
        render_messages_tab(broker_opps_all, sel_id, sel_name)

    with tab3:
        tx_df = load_transactions()
        render_analysis_tab(broker_opps_all, feat_df, tx_df, sel_id, sel_name, churn_scores)


if __name__ == '__main__':
    main()

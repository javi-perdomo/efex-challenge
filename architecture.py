"""
Genera diagrama de arquitectura del sistema EFEX AI.
Run: python architecture.py
Genera outputs/architecture.png
"""
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import os

def draw_architecture():
    os.makedirs('outputs', exist_ok=True)
    fig, ax = plt.subplots(1, 1, figsize=(16, 10))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 10)
    ax.axis('off')
    ax.set_facecolor('#F8F9FA')
    fig.patch.set_facecolor('#F8F9FA')

    def box(x, y, w, h, label, sublabel='', color='#2196F3', text_color='white', fontsize=10):
        rect = FancyBboxPatch((x, y), w, h,
                              boxstyle="round,pad=0.1",
                              facecolor=color, edgecolor='white',
                              linewidth=2, zorder=3)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h/2 + (0.15 if sublabel else 0), label,
                ha='center', va='center', color=text_color,
                fontsize=fontsize, fontweight='bold', zorder=4)
        if sublabel:
            ax.text(x + w/2, y + h/2 - 0.25, sublabel,
                    ha='center', va='center', color=text_color,
                    fontsize=8, zorder=4, style='italic')

    def arrow(x1, y1, x2, y2):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', color='#455A64', lw=2),
                    zorder=5)

    # Title
    ax.text(8, 9.4, 'EFEX AI — Arquitectura del Sistema',
            ha='center', va='center', fontsize=16, fontweight='bold', color='#1A237E')
    ax.text(8, 9.0, 'Sistema de Recomendaciones para Brokers FX',
            ha='center', va='center', fontsize=11, color='#546E7A', style='italic')

    # Layer 1: Data
    box(0.5, 7.0, 2.5, 1.0, 'transactions_anonymized', '.xlsx (176k filas)', color='#607D8B', fontsize=9)

    # Layer 2: EDA
    box(3.5, 7.0, 2.0, 1.0, 'EDA', 'eda.py', color='#9C27B0', fontsize=10)

    # Layer 3: Feature Engineering
    box(6.0, 7.0, 2.5, 1.0, 'Feature Engineering', 'features.py', color='#1976D2', fontsize=9)

    # RFM below feature eng
    box(6.5, 5.5, 1.5, 1.0, 'RFM Scoring', 'Segmentación', color='#0288D1', fontsize=8)

    # Layer 4: Opportunity Engine
    box(9.0, 7.0, 2.5, 1.0, 'Opportunity Engine', 'opportunities.py', color='#388E3C', fontsize=9)

    # Layer 5: LLM
    box(12.0, 6.2, 3.0, 1.0, 'Ollama LLM', 'llama3.2 / mistral', color='#F57C00', fontsize=9)

    # Layer 5b: Message Generator
    box(12.0, 4.7, 3.0, 1.0, 'Message Generator', 'message_generator.py', color='#E64A19', fontsize=9)

    # Layer 6: Dashboard
    box(5.5, 2.5, 5.0, 1.5, 'Streamlit Dashboard', 'app.py — Broker Copilot', color='#AD1457', fontsize=11)

    # Output boxes
    box(0.5, 4.5, 1.8, 0.8, 'EDA Plots', '/outputs/eda/', color='#78909C', fontsize=8)
    box(0.5, 3.3, 1.8, 0.8, 'features', '.parquet', color='#78909C', fontsize=8)
    box(2.7, 3.3, 1.8, 0.8, 'opportunities', '.parquet', color='#78909C', fontsize=8)

    # Dashboard tabs
    tab_colors = ['#C2185B', '#AD1457', '#880E4F']
    tab_labels = ['Tab 1\nOportunidades', 'Tab 2\nMensajes WA', 'Tab 3\nAnálisis']
    for i, (c, l) in enumerate(zip(tab_colors, tab_labels)):
        box(4.5 + i*2.5, 1.0, 2.2, 1.0, l, color=c, fontsize=8)

    # Arrows
    arrow(3.0, 7.5, 3.5, 7.5)      # data → eda
    arrow(5.5, 7.5, 6.0, 7.5)      # eda → features
    arrow(7.25, 7.0, 7.25, 6.5)    # features → rfm
    arrow(7.25, 5.5, 7.25, 5.0)    # rfm down
    arrow(8.5, 7.5, 9.0, 7.5)      # features → opportunities
    arrow(11.5, 7.5, 12.0, 6.9)    # opps → ollama
    arrow(13.5, 6.2, 13.5, 5.7)    # ollama → msg gen
    arrow(11.5, 5.2, 8.5, 3.5)     # msg gen → dashboard
    arrow(9.5, 7.0, 8.0, 4.0)      # opps → dashboard
    arrow(2.3, 4.5, 2.3, 4.1)      # eda → eda plots
    arrow(1.4, 7.0, 1.4, 5.3)      # data → features parquet
    arrow(3.6, 7.0, 3.6, 4.1)      # opps → opp parquet

    # Legend
    legend_items = [
        ('#607D8B', 'Datos'),
        ('#1976D2', 'Procesamiento'),
        ('#388E3C', 'Motor de Reglas'),
        ('#F57C00', 'LLM Local'),
        ('#AD1457', 'UI / Dashboard'),
        ('#78909C', 'Outputs'),
    ]
    for i, (c, l) in enumerate(legend_items):
        rect = FancyBboxPatch((0.5 + i*2.5, 0.2), 1.5, 0.4,
                              boxstyle="round,pad=0.05", facecolor=c, edgecolor='white', zorder=3)
        ax.add_patch(rect)
        ax.text(1.25 + i*2.5, 0.4, l, ha='center', va='center',
                color='white', fontsize=8, fontweight='bold', zorder=4)

    plt.tight_layout()
    plt.savefig('outputs/architecture.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Guardado: outputs/architecture.png")

if __name__ == '__main__':
    draw_architecture()

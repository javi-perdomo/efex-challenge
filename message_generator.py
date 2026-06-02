"""
Generador de mensajes WhatsApp usando Ollama (llama3.2 o mistral).
Fallback automático a templates si Ollama no está disponible.
Run: python message_generator.py <broker_id>
"""
import json
import os
import requests
import pandas as pd
import sys
import warnings
warnings.filterwarnings('ignore')

OLLAMA_URL = 'http://localhost:11434'
PREFERRED_MODEL = 'llama3.2'
FALLBACK_MODEL = 'mistral'
OUTPUT_PATH = 'outputs/messages.json'

DAYS_OF_WEEK = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

EMOJI_MAP = {
    'CHURN_RISK': '🚨',
    'REACTIVATION': '💤',
    'UPSELL': '📈',
    'BEST_TIME': '🕐',
}

def check_ollama():
    """Verifica si Ollama está disponible y retorna el modelo a usar."""
    try:
        resp = requests.get(f'{OLLAMA_URL}/api/tags', timeout=3)
        if resp.status_code == 200:
            models = [m['name'] for m in resp.json().get('models', [])]
            for m in [PREFERRED_MODEL, FALLBACK_MODEL]:
                for available in models:
                    if m in available:
                        return available
            # If no preferred model, use whatever is available
            if models:
                return models[0]
    except Exception:
        pass
    return None

def build_prompt(row):
    day_name = DAYS_OF_WEEK[int(row['preferred_day'])] if int(row['preferred_day']) < 7 else 'entre semana'
    trend_label = 'en crecimiento' if row['volume_trend'] > 0 else ('en caída' if row['volume_trend'] < 0 else 'estable')

    opp_descriptions = {
        'CHURN_RISK': f"este cliente lleva {row['days_since_last_tx']:.0f} días sin operar y está en riesgo de perderse",
        'REACTIVATION': f"este cliente lleva {row['days_since_last_tx']:.0f} días inactivo y tiene potencial de reactivación",
        'UPSELL': f"este cliente está activo y su volumen está {trend_label}, es momento de aumentar el negocio",
        'BEST_TIME': f"el mejor momento para contactar a este cliente es los {day_name} a las {row['preferred_hour']}:00",
    }

    situation = opp_descriptions.get(row['opportunity_type'], 'hay una oportunidad comercial')

    return f"""Eres el asistente AI de EFEX, una fintech de cambio de divisas (FX) entre México y Estados Unidos.
Genera un mensaje de WhatsApp en español para un broker/promotor de EFEX sobre uno de sus clientes.

DATOS DEL CLIENTE:
- Nombre: {row['client_name']}
- Situación: {situation}
- Volumen histórico total: ${row['total_volume_usd']:,.0f} USD
- Volumen promedio por transacción: ${row['avg_volume_usd']:,.0f} USD
- Tendencia de volumen: {trend_label}
- Mejor hora para contactar: {day_name} a las {row['preferred_hour']}:00
- Segmento: {row['segment']}

FORMATO REQUERIDO (máximo 150 palabras, usa estos emojis exactos):
🔔 [{row['opportunity_type']}]
Cliente: {row['client_name']}

📊 Situación: [qué está pasando con este cliente]
💡 Por qué importa: [impacto en el negocio del broker]
✅ Acción sugerida: [qué hacer y cuándo hacerlo]

— EFEX AI

Sé directo, concreto y accionable. NO uses más de 150 palabras."""

def generate_with_ollama(row, model):
    """Llama a Ollama para generar un mensaje."""
    prompt = build_prompt(row)
    try:
        resp = requests.post(
            f'{OLLAMA_URL}/api/generate',
            json={'model': model, 'prompt': prompt, 'stream': False, 'options': {'num_predict': 300}},
            timeout=60
        )
        if resp.status_code == 200:
            return resp.json().get('response', '').strip()
    except Exception as e:
        pass
    return None

def generate_template(row):
    """Fallback: genera mensaje con template cuando Ollama no está disponible."""
    emoji = EMOJI_MAP.get(row['opportunity_type'], '🔔')
    day_name = DAYS_OF_WEEK[int(row['preferred_day'])] if int(row['preferred_day']) < 7 else 'entre semana'
    trend_label = 'en crecimiento' if row['volume_trend'] > 0 else ('a la baja' if row['volume_trend'] < 0 else 'estable')

    templates = {
        'CHURN_RISK': (
            f"🔔 [CHURN_RISK]\n"
            f"Cliente: {row['client_name']}\n\n"
            f"📊 Situación: Lleva {row['days_since_last_tx']:.0f} días sin operar. "
            f"Su volumen histórico es de ${row['total_volume_usd']:,.0f} USD.\n"
            f"💡 Por qué importa: Este cliente representa un riesgo de churn de alto valor. "
            f"Perderlo impacta directamente tu comisión.\n"
            f"✅ Acción sugerida: Contáctalo hoy. "
            f"Pregúntale si tiene necesidades de cambio de divisas pendientes. "
            f"Mejor hora: {day_name} {row['preferred_hour']}:00.\n\n— EFEX AI"
        ),
        'REACTIVATION': (
            f"🔔 [REACTIVATION]\n"
            f"Cliente: {row['client_name']}\n\n"
            f"📊 Situación: Inactivo {row['days_since_last_tx']:.0f} días. "
            f"Operó ${row['total_volume_usd']:,.0f} USD en total contigo.\n"
            f"💡 Por qué importa: Reactivar un cliente existente cuesta 5x menos que adquirir uno nuevo.\n"
            f"✅ Acción sugerida: Envíale un recordatorio con el tipo de cambio del día. "
            f"Mejor contactarlo el {day_name} a las {row['preferred_hour']}:00.\n\n— EFEX AI"
        ),
        'UPSELL': (
            f"🔔 [UPSELL]\n"
            f"Cliente: {row['client_name']}\n\n"
            f"📊 Situación: Cliente activo con volumen {trend_label}. "
            f"Promedio de ${row['avg_volume_usd']:,.0f} USD por operación.\n"
            f"💡 Por qué importa: Está en el mejor momento para aumentar el ticket promedio o frecuencia.\n"
            f"✅ Acción sugerida: Ofrécele condiciones preferenciales para operaciones mayores a ${row['avg_volume_usd']*1.5:,.0f} USD. "
            f"Contáctalo el {day_name} a las {row['preferred_hour']}:00.\n\n— EFEX AI"
        ),
        'BEST_TIME': (
            f"🔔 [BEST_TIME]\n"
            f"Cliente: {row['client_name']}\n\n"
            f"📊 Situación: Cliente activo. Su patrón histórico muestra mayor actividad "
            f"los {day_name} a las {row['preferred_hour']}:00.\n"
            f"💡 Por qué importa: Contactar en el momento correcto aumenta la tasa de conversión.\n"
            f"✅ Acción sugerida: Programa tu mensaje para el próximo {day_name} a las {row['preferred_hour']}:00.\n\n— EFEX AI"
        ),
    }
    return templates.get(row['opportunity_type'], f"🔔 Oportunidad detectada para {row['client_name']}.")

def generate_batch(broker_id, opp_df=None, use_ollama=True, model=None, save=True, progress_callback=None):
    """Genera todos los mensajes para un broker específico.
    progress_callback(current, total, client_name, opp_type, source) se llama después de cada mensaje.
    """
    if opp_df is None:
        if not os.path.exists('outputs/opportunities.parquet'):
            import opportunities
            opp_df = opportunities.detect_opportunities(opportunities.load_features())
        else:
            opp_df = pd.read_parquet('outputs/opportunities.parquet')

    broker_opps = opp_df[opp_df['broker_id'] == broker_id]
    if len(broker_opps) == 0:
        print(f"No hay oportunidades para broker {broker_id}")
        return []

    results = []
    total = len(broker_opps)
    for i, (_, row) in enumerate(broker_opps.iterrows()):
        print(f"  [{i+1}/{total}] {row['opportunity_type']} - {row['client_name']}...", end=' ')
        if use_ollama and model:
            msg = generate_with_ollama(row, model)
            if msg:
                source = 'ollama'
            else:
                msg = generate_template(row)
                source = 'template'
        else:
            msg = generate_template(row)
            source = 'template'
        print(f"({source})")
        if progress_callback:
            progress_callback(i + 1, total, row['client_name'], row['opportunity_type'], source)
        results.append({
            'broker_id': broker_id,
            'broker_name': row['broker_name'],
            'client_id': row['client_id'],
            'client_name': row['client_name'],
            'opportunity_type': row['opportunity_type'],
            'priority': row['priority'],
            'message': msg,
            'source': source,
            'context': row['context'],
        })

    if save:
        os.makedirs('outputs', exist_ok=True)
        # Load existing messages and merge
        existing = []
        if os.path.exists(OUTPUT_PATH):
            with open(OUTPUT_PATH) as f:
                existing = json.load(f)
        # Remove old messages for this broker
        existing = [m for m in existing if m.get('broker_id') != broker_id]
        existing.extend(results)
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        print(f"Guardado: {OUTPUT_PATH} ({len(results)} mensajes para broker)")

    return results

if __name__ == '__main__':
    os.makedirs('outputs', exist_ok=True)
    model = check_ollama()
    if model:
        print(f"Ollama disponible. Usando modelo: {model}")
    else:
        print("Ollama no disponible. Usando templates de fallback.")

    if len(sys.argv) > 1:
        broker_id = sys.argv[1]
    else:
        # Use first broker in opportunities
        if os.path.exists('outputs/opportunities.parquet'):
            opp_df = pd.read_parquet('outputs/opportunities.parquet')
        else:
            import opportunities
            opp_df = opportunities.detect_opportunities(opportunities.load_features())
        broker_id = opp_df['broker_id'].iloc[0]
        print(f"Usando primer broker del dataset: {broker_id}")

    results = generate_batch(broker_id, use_ollama=(model is not None), model=model)
    print(f"\nGenerados {len(results)} mensajes.")

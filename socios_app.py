import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

st.set_page_config(page_title="AutoSplit", layout="wide")
st.title("🚗 AutoSplit")

SHEET_HEADERS = [
    'id', 'vehiculo', 'fecha_compra', 'compra', 'gastos',
    'costo_total', 'inversion_tu', 'inversion_socio',
    'venta', 'fecha_venta', 'ganancia', 'tu_ganancia_30', 'socio_ganancia_70', 'status'
]

@st.cache_resource
def get_gspread_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    return gspread.authorize(creds)

def get_sheet():
    client = get_gspread_client()
    return client.open_by_key(st.secrets["sheet_id"]).sheet1

def load_data():
    try:
        sheet = get_sheet()
        records = sheet.get_all_records()
        data = []
        for r in records:
            op = dict(r)
            # gastos se guarda como string JSON en la hoja
            gastos_raw = op.get('gastos', '[]')
            try:
                op['gastos'] = json.loads(gastos_raw) if gastos_raw else []
            except Exception:
                op['gastos'] = []
            if not isinstance(op['gastos'], list):
                op['gastos'] = []
            # Convertir tipos numéricos
            for campo in ['id', 'compra', 'costo_total', 'inversion_tu', 'inversion_socio',
                          'venta', 'ganancia', 'tu_ganancia_30', 'socio_ganancia_70']:
                try:
                    op[campo] = float(op[campo]) if op[campo] != '' else 0.0
                except Exception:
                    op[campo] = 0.0
            data.append(op)
        return data
    except Exception:
        return []

def save_data(data):
    sheet = get_sheet()
    sheet.clear()
    sheet.append_row(SHEET_HEADERS)
    for op in data:
        row = []
        for h in SHEET_HEADERS:
            val = op.get(h, '')
            if h == 'gastos':
                val = json.dumps(val, ensure_ascii=False)
            row.append(val)
        sheet.append_row(row)

if 'data' not in st.session_state:
    st.session_state.data = load_data()
else:
    st.session_state.data = load_data()

moneda = st.sidebar.selectbox("💱 Moneda", ["USD $", "ARS $"], key="moneda")
simbolo = "$" if moneda == "USD $" else "$"

# 📥 NUEVA COMPRA
st.sidebar.header("📥 Nueva Compra")
vehiculo = st.sidebar.text_input("Auto", key="vehiculo_nuevo")
compra = st.sidebar.number_input("Precio compra", min_value=0.0, key="compra_nueva")

if st.sidebar.button("✅ Registrar", key="btn_registrar") and vehiculo:
    op = {
        'id': len(st.session_state.data) + 1,
        'vehiculo': vehiculo,
        'fecha_compra': datetime.now().strftime('%d/%m/%Y %H:%M'),
        'compra': round(compra, 0),
        'gastos': [],  # SIEMPRE lista
        'costo_total': round(compra, 0),
        'inversion_tu': round(compra / 2, 0),
        'inversion_socio': round(compra / 2, 0),
        'venta': 0,
        'fecha_venta': '',
        'ganancia': 0,
        'tu_ganancia_30': 0,
        'socio_ganancia_70': 0,
        'status': 'pendiente'
    }
    st.session_state.data.append(op)
    save_data(st.session_state.data)
    st.sidebar.success(f"✅ Creado {simbolo}{compra:,.0f}")
    st.rerun()

# 🔧 GASTOS MÚLTIPLES
st.sidebar.header("🔧 Gastos Extra")
pendientes_gastos = [op for op in st.session_state.data if op['status'] == 'pendiente']
if pendientes_gastos:
    opciones_gasto = [f"{op['id']}. {op['vehiculo']} ({simbolo}{op['costo_total']:,.0f})" for op in pendientes_gastos]
    auto_gasto = st.sidebar.selectbox("Auto", opciones_gasto, key="select_gasto")
    desc_gasto = st.sidebar.text_input("Descripción", key="desc_gasto")
    monto_gasto = st.sidebar.number_input("Monto", min_value=0.0, key="monto_gasto")
    pagador_gasto = st.sidebar.selectbox("¿Quién pagó?", ["Daiana", "Gustavo"], key="pagador_gasto")

    if st.sidebar.button("➕ Agregar", key="btn_gasto") and monto_gasto > 0:
        id_auto = int(auto_gasto.split('.')[0])
        for op in st.session_state.data:
            if op['id'] == id_auto:
                # ASEGURAR lista
                if not isinstance(op['gastos'], list):
                    op['gastos'] = []
                fecha_gasto = datetime.now().strftime('%d/%m %H:%M')
                op['gastos'].append({
                    'fecha': fecha_gasto,
                    'desc': desc_gasto,
                    'monto': round(monto_gasto, 0),
                    'pagador': pagador_gasto
                })
                op['costo_total'] += round(monto_gasto, 0)
                op['inversion_tu'] = round(op['costo_total'] / 2, 0)
                op['inversion_socio'] = round(op['costo_total'] / 2, 0)
                break
        save_data(st.session_state.data)
        st.sidebar.success("✅ Gasto agregado")
        st.rerun()

# 💰 VENTA
st.sidebar.header("💰 Vender")
pendientes_venta = [op for op in st.session_state.data if op['status'] == 'pendiente']
if pendientes_venta:
    opciones_venta = [f"{op['id']}. {op['vehiculo']} ({simbolo}{op['costo_total']:,.0f})" for op in pendientes_venta]
    veh_sel = st.sidebar.selectbox("Auto", opciones_venta, key="select_venta")
    venta = st.sidebar.number_input("Precio venta", min_value=0.0, key="precio_venta")
    
    if st.sidebar.button("💵 Cerrar", key="btn_vender") and venta > 0:
        id_auto = int(veh_sel.split('.')[0])
        for op in st.session_state.data:
            if op['id'] == id_auto:
                ganancia = venta - op['costo_total']
                op['venta'] = round(venta, 0)
                op['fecha_venta'] = datetime.now().strftime('%d/%m/%Y %H:%M')
                op['ganancia'] = round(ganancia, 0)
                op['tu_ganancia_30'] = round(ganancia * 0.3, 0)
                op['socio_ganancia_70'] = round(ganancia * 0.7, 0)
                op['status'] = 'vendido'
                break
        save_data(st.session_state.data)
        st.sidebar.success(f"💰 Ganancia {simbolo}{ganancia:,.0f}")
        st.rerun()

# 🗑️ ELIMINAR
st.sidebar.header("🗑️ Eliminar")
if st.session_state.data:
    todos_autos = [f"{op['id']}. {op['vehiculo']} ({op['status']})" for op in st.session_state.data]
    auto_eliminar = st.sidebar.selectbox("Para BORRAR", todos_autos, key="select_eliminar")
    if st.sidebar.button("🗑️ ELIMINAR", type="primary", key="btn_eliminar"):
        id_eliminar = int(auto_eliminar.split('.')[0])
        st.session_state.data = [op for op in st.session_state.data if op['id'] != id_eliminar]
        for i, op in enumerate(st.session_state.data):
            op['id'] = i + 1
        save_data(st.session_state.data)
        st.sidebar.error("🗑️ ELIMINADO")
        st.rerun()

# 📊 DASHBOARD
st.header(f"📋 Registro de Operaciones ({moneda})")
if st.session_state.data:
    # FIX DEFINITIVO: Función segura
    def get_gastos_total(gastos):
        if not gastos or gastos == []:
            return 0
        if isinstance(gastos, list):
            return sum(g['monto'] for g in gastos if isinstance(g, dict))
        return 0

    gastos_totals = [get_gastos_total(op['gastos']) for op in st.session_state.data]

    df = pd.DataFrame(st.session_state.data)
    df['gastos_total'] = gastos_totals

    # Tabla con colores por estado
    display_cols = ['vehiculo', 'fecha_compra', 'compra', 'gastos_total', 'costo_total',
                    'venta', 'fecha_venta', 'ganancia', 'tu_ganancia_30', 'socio_ganancia_70', 'status']
    col_rename = {
        'vehiculo': 'Auto', 'fecha_compra': 'F. Compra', 'compra': 'Compra',
        'gastos_total': 'Gastos', 'costo_total': 'Costo Total', 'venta': 'Venta',
        'fecha_venta': 'F. Venta', 'ganancia': 'Ganancia',
        'tu_ganancia_30': 'Vos (30%)', 'socio_ganancia_70': 'Socio (70%)', 'status': 'Estado'
    }
    display_df = df[display_cols].rename(columns=col_rename).copy()

    # Quitar hora de las fechas
    for col_fecha in ['F. Compra', 'F. Venta']:
        display_df[col_fecha] = display_df[col_fecha].apply(
            lambda x: x.split(' ')[0] if isinstance(x, str) and x else '—'
        )

    # Formato numérico: 2 decimales
    num_cols = ['Compra', 'Gastos', 'Costo Total', 'Venta', 'Ganancia', 'Vos (30%)', 'Socio (70%)']
    for c in num_cols:
        display_df[c] = pd.to_numeric(display_df[c], errors='coerce').round(2)

    def color_row(row):
        if row['Estado'] == 'vendido':
            c = 'rgba(0,180,0,0.13)' if row['Ganancia'] >= 0 else 'rgba(200,0,0,0.18)'
        else:
            c = 'rgba(255,190,0,0.10)'
        return [f'background-color: {c}'] * len(row)

    st.dataframe(display_df.style.apply(color_row, axis=1), use_container_width=True)

    cerradas = [op for op in st.session_state.data if op['status'] == 'vendido']
    gan_daiana = sum(op['tu_ganancia_30'] for op in cerradas)
    gan_gustavo = sum(op['socio_ganancia_70'] for op in cerradas)

    # Gastos pagados por cada uno (solo registros con pagador)
    gast_daiana = sum(
        g['monto'] for op in cerradas
        for g in op.get('gastos', [])
        if isinstance(g, dict) and g.get('pagador') == 'Daiana'
    )
    gast_gustavo = sum(
        g['monto'] for op in cerradas
        for g in op.get('gastos', [])
        if isinstance(g, dict) and g.get('pagador') == 'Gustavo'
    )
    inversion_base = sum(op['compra'] / 2 for op in cerradas)

    rec_daiana = inversion_base + gast_daiana + gan_daiana
    rec_gustavo = inversion_base + gast_gustavo + gan_gustavo

    st.markdown("""
    <style>
    div[data-testid="column"] { min-width: 45% !important; flex: 1 1 45% !important; }
    </style>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)
    with col1:
        st.metric("💵 Ganancia Daiana (30%)", f"{simbolo} {gan_daiana:,.0f}")
    with col2:
        st.metric("👥 Ganancia Gustavo (70%)", f"{simbolo} {gan_gustavo:,.0f}")
    with col3:
        st.metric("🔄 Recupero Daiana", f"{simbolo} {rec_daiana:,.0f}")
    with col4:
        st.metric("🔄 Recupero Gustavo", f"{simbolo} {rec_gustavo:,.0f}")

    # DETALLE GASTOS
    st.subheader("📋 Detalle Gastos")
    for op in st.session_state.data:
        gastos_total = get_gastos_total(op['gastos'])
        if gastos_total > 0:
            with st.expander(f"{op['id']}. {op['vehiculo']} ({len(op['gastos'])} gastos - {simbolo}{gastos_total:,.0f})"):
                for gasto in op['gastos']:
                    if isinstance(gasto, dict):
                        pagador = gasto.get('pagador', '?')
                        st.write(f"**{gasto['fecha']}** - {gasto['desc']}: {simbolo}{gasto['monto']:,.0f} — pagó **{pagador}**")

    st.download_button("📥 Excel", df.to_csv(index=False), f"cuentas_{moneda.replace(' ', '_')}.csv", "text/csv")
else:
    st.info("👈 Primera compra")

st.sidebar.markdown("---")
if st.sidebar.button("🗑️ LIMPIAR TODO", key="btn_limpiar"):
    st.session_state.data = []
    save_data([])
    st.rerun()

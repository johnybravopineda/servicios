import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Primos Spa - Gestión Terreno", page_icon="⚡", layout="centered")

# --- CSS PERSONALIZADO PARA ACHICAR INTERLINEADO Y ESPACIOS ---
st.markdown("""
    <style>
    /* Reducir el espacio superior de la página */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    /* Reducir espacio entre widgets (interlineado general) */
    div.stVerticalBlock > div {
        gap: 0.6rem !important;
    }
    /* Ajustar etiquetas (labels) para que estén más cerca del campo */
    .st-emotion-cache-1p2n659 p, label {
        margin-bottom: 0px !important;
        line-height: 1.2 !important;
        font-weight: 600;
    }
    /* Reducir margen de los inputs numéricos y áreas de texto */
    div.stNumberInput, div.stTextArea, div.stSelectbox {
        margin-bottom: -10px;
    }
    /* Estilo para el título de Primos Spa */
    .main-title {
        color: #004280;
        margin-bottom: 0px;
    }
    </style>
    """, unsafe_allow_html=True)

DB_NAME = "datos_terreno.db"
EXCEL_MAESTRO = "datos.xlsx"

# --- FUNCIONES DE BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS mediciones
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  fecha TEXT, hora TEXT, proyecto TEXT, lote TEXT, 
                  energia REAL, agua REAL, observaciones TEXT)''')
    conn.commit()
    conn.close()

def verificar_duplicado(proyecto, lote, fecha):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id FROM mediciones WHERE proyecto=? AND lote=? AND fecha=?", (proyecto, lote, fecha))
    resultado = c.fetchone()
    conn.close()
    return resultado is not None

def guardar_local(proyecto, lote, energia, agua, obs):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        ahora = datetime.now()
        fecha_str = ahora.strftime("%d-%m-%Y")
        hora_str = ahora.strftime("%H:%M:%S")
        c.execute("""INSERT INTO mediciones (fecha, hora, proyecto, lote, energia, agua, observaciones) 
                     VALUES (?, ?, ?, ?, ?, ?, ?)""", (fecha_str, hora_str, proyecto, lote, energia, agua, str(obs)))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

# --- LÓGICA DE INICIO ---
init_db()

if 'confirmar' not in st.session_state:
    st.session_state.confirmar = False

@st.cache_data
def get_maestro():
    if os.path.exists(EXCEL_MAESTRO):
        return pd.read_excel(EXCEL_MAESTRO)
    return pd.DataFrame({"Proyecto": ["DEMO"], "Lote": ["001"]})

df_maestro = get_maestro()

# --- INTERFAZ COMPACTA ---
st.markdown("<h1 class='main-title'>⚡ Primos Spa</h1>", unsafe_allow_html=True)
st.caption("Control de Mediciones | Copiapó")

# 1. SELECCIÓN (Reactiva fuera del form)
col_p, col_l = st.columns(2)
with col_p:
    p_sel = st.selectbox("Proyecto", sorted(df_maestro["Proyecto"].unique()))
with col_l:
    l_sel = st.selectbox("Lote", sorted(df_maestro[df_maestro["Proyecto"] == p_sel]["Lote"].unique()))

# 2. FORMULARIO CON RESET Y ESPACIO COMPACTO
id_ui = f"{p_sel}_{l_sel}"

with st.form("form_compacto", clear_on_submit=True):
    st.write(f"✍️ **Punto:** {l_sel}")
    
    c1, c2 = st.columns(2)
    with c1:
        val_en = st.number_input("Energía (kWh)", value=None, key=f"e_{id_ui}")
    with c2:
        val_ag = st.number_input("Agua (m³)", value=None, key=f"a_{id_ui}")
    
    txt_obs = st.text_area("Observaciones", max_chars=256, key=f"o_{id_ui}", height=70)
    
    btn_save = st.form_submit_button("💾 GUARDAR DATOS")

# 3. VALIDACIÓN Y DUPLICADOS
if btn_save:
    if val_en is not None and val_ag is not None:
        hoy = datetime.now().strftime("%d-%m-%Y")
        if verificar_duplicado(p_sel, l_sel, hoy):
            st.session_state.confirmar = True
            st.session_state.tmp = (p_sel, l_sel, val_en, val_ag, txt_obs)
        else:
            if guardar_local(p_sel, l_sel, val_en, val_ag, txt_obs):
                st.success("Guardado.")
                st.rerun()
    else:
        st.warning("Complete kWh y m³.")

if st.session_state.confirmar:
    st.warning("⚠️ Ya existe registro hoy.")
    cs, cn = st.columns(2)
    with cs:
        if st.button("✅ Duplicar"):
            p, l, e, a, o = st.session_state.tmp
            guardar_local(p, l, e, a, o)
            st.session_state.confirmar = False
            st.rerun()
    with cn:
        if st.button("❌ Cancelar"):
            st.session_state.confirmar = False
            st.rerun()

# 4. HISTORIAL
st.divider()
conn = sqlite3.connect(DB_NAME)
df_local = pd.read_sql_query("SELECT fecha, hora, proyecto, lote, energia, agua, observaciones FROM mediciones ORDER BY id DESC", conn)
conn.close()

if not df_local.empty:
    st.dataframe(df_local, use_container_width=True, hide_index=True)
    csv = df_local.to_csv(index=False, sep=';').encode('utf-8-sig')
    st.download_button("📥 Bajar CSV", data=csv, file_name=f"primos_spa_{datetime.now().strftime('%Y%m%d')}.csv")
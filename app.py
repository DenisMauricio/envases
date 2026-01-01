# app.py
import streamlit as st
import pandas as pd
from datetime import date, datetime
import gspread
from google.oauth2.service_account import Credentials

# -----------------------------
# CONFIGURACIÓN DE SERVICE ACCOUNT
# -----------------------------

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# --- ANTES (Local con archivo) ---
# SERVICE_ACCOUNT_FILE = "credenciales.json"
# creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

# --- AHORA (Seguro para la nube) ---
# 'gcp_service_account' es el nombre que le pondremos en el panel de Streamlit
creds_dict = st.secrets["gcp_service_account"]
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)

gc = gspread.authorize(creds)

# -----------------------------
# URLS DE GOOGLE SHEETS
# -----------------------------
CLIENTES_SHEET_URL = "https://docs.google.com/spreadsheets/d/1QGlekZVaAK7bqvy8UlIdHNtconvnsC-BGUIVL4ScR_8"
REGISTRO_SHEET_URL = "https://docs.google.com/spreadsheets/d/1UngJ-kSTTyoSVKMnEpgxyWXOE8Rz0iO_RjjsIXH2zvI"

# -----------------------------
# Función para cargar clientes
# -----------------------------
@st.cache_data
def cargar_clientes():
    sh_clientes = gc.open_by_url(CLIENTES_SHEET_URL)
    worksheet_clientes = sh_clientes.sheet1  # primera pestaña
    data = worksheet_clientes.get_all_records()
    df = pd.DataFrame(data)
    return df

clientes_df = cargar_clientes()



st.title("🚛📦 Formulario de envases")

# -----------------------------
# Inputs principales
# -----------------------------
codigo_sn = st.selectbox(
    "Código SN",
    options=clientes_df["CodigoSN"].tolist(),
    index=0
)

# Obtener datos del cliente seleccionado
cliente = clientes_df[clientes_df["CodigoSN"] == codigo_sn].iloc[0]

def to_int_safe(value):
    try:
        if value is None:
            return 0

        s = str(value).strip()

        if s in ("", "-", "—"):
            return 0

        # Caso formato latino: 1.234,56
        if "," in s and "." in s:
            s = s.replace(".", "").split(",")[0]

        # Caso decimal con coma: 646,00
        elif "," in s:
            s = s.split(",")[0]

        # Caso miles con punto: 1.234
        elif "." in s:
            s = s.replace(".", "") # Acá está llegando 1.051,00 como 1051

        else:
            return int(int(s) / 100) #Si no contiene ni puntos, ni comas
        
        return int(s)

    except ValueError:
        return 0

st.text_input("Nombre SN", cliente["NombreSN"], disabled=True)
st.text_input("Vendedor", cliente["Vendedor"], disabled=True)
st.number_input("Envases Azules", value=to_int_safe(cliente["ENVASESAZULES"]), disabled=True)
st.number_input("Envases Negros", value=to_int_safe(cliente["ENVASESNEGROS"]), disabled=True)

# -----------------------------
# Función de inputs con fecha
# -----------------------------
def input_envases(label, con_fecha=True, texto_fecha="Fecha"):
    if con_fecha:
        col1, col2 = st.columns([2, 1])
        with col1:
            valor = st.number_input(label, min_value=0, key=f"num_{label}")
        with col2:
            fecha = st.date_input(texto_fecha, None, key=f"fecha_{label}") # date.today()
        return valor, fecha
    else:
        valor = st.number_input(label, min_value=0, key=f"num_{label}")
        return valor, None

# Vacíos
azules_vacios, fecha_azules = input_envases("Envases Azules Vacíos", True, "Fecha Recojo")
negros_vacios, fecha_negros = input_envases("Envases Negros Vacíos", True, "Fecha Recojo")
competencia_vacios, _ = input_envases("Envases Competencia Vacíos", False)

# Llenos
azules_llenos, fecha_venc_azules = input_envases("Envases Azules Llenos", True, "Fecha Vencimiento")
negros_llenos, fecha_venc_negros = input_envases("Envases Negros Llenos", True, "Fecha Vencimiento")
competencia_llenos, _ = input_envases("Envases Competencia Llenos", False)

# Comentarios
comentarios = st.text_area("Comentarios", height=100)

# -----------------------------
# Función para guardar en Google Sheet
# -----------------------------
def guardar_en_google_sheet(registro):
    sh_registro = gc.open_by_url(REGISTRO_SHEET_URL)
    worksheet = sh_registro.sheet1  # primera pestaña

    # Revisar si hay cabecera
    header = worksheet.row_values(1)
    if not header:
        header = list(registro.keys())
        worksheet.append_row(header)

    # Convertir registro a fila ordenada según header
    fila = [registro.get(h, "") for h in header]
    worksheet.append_row(fila)

def limpiar_formulario():
    defaults = {
        "codigo_sn": "C000037100",
        "comentarios": "",
        "azules_vacios": 0,
        "negros_vacios": 0,
        "competencia_vacios": 0,
        "azules_llenos": 0,
        "negros_llenos": 0,
        "competencia_llenos": 0,
        "fecha_recojo_azules": None,
        "fecha_recojo_negros": None,
        "fecha_venc_azules": None,
        "fecha_venc_negros": None,
    }

    for k, v in defaults.items():
        st.session_state[k] = v

# -----------------------------
# Botón Guardar
# -----------------------------
registro = {
    "FechaRegistro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "CodigoSN": cliente["CodigoSN"],
    "NombreSN": cliente["NombreSN"],
    "Vendedor": cliente["Vendedor"],
    "EnvasesActualesAzules": cliente["ENVASESAZULES"],
    "EnvasesActualesNegros": cliente["ENVASESNEGROS"],
    "AzulesVacios": azules_vacios,
    "FechaRecojoAzules": fecha_azules.strftime("%Y-%m-%d") if fecha_azules else "",
    "NegrosVacios": negros_vacios,
    "FechaRecojoNegros": fecha_negros.strftime("%Y-%m-%d") if fecha_negros else "",
    "CompetenciaVacios": competencia_vacios,
    "AzulesLlenos": azules_llenos,
    "FechaVencAzules": fecha_venc_azules.strftime("%Y-%m-%d") if fecha_venc_azules else "",
    "NegrosLlenos": negros_llenos,
    "FechaVencNegros": fecha_venc_negros.strftime("%Y-%m-%d") if fecha_venc_negros else "",
    "CompetenciaLlenos": competencia_llenos,
    "Comentarios": comentarios
}

# Botón para Guardar formulario
if st.button("Guardar"):
    exito = guardar_en_google_sheet(registro)
    if exito:
        st.toast("🍻✅ Registro guardado con éxito")

        limpiar_formulario()

# Botón para guardar geolocalización
URL = "https://script.google.com/macros/s/AKfycbyuTVIKeUTWC3Vy70uQOFU4Xic9ZOBpF5sLNhi_m303rIcAivp4kPaPZpqLbmTmH4fy/exec"

st.markdown(
    f"[🌎 Presiona para guardar geolocalización]({URL})",
    unsafe_allow_html=True
)
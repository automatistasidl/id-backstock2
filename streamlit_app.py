import streamlit as st
import pandas as pd
import pytz
import requests
from io import StringIO
from datetime import datetime
from streamlit_option_menu import option_menu
import streamlit.components.v1 as components
import time

# --- GOOGLE SHEETS CONFIG ---
import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_KEY = st.secrets["spreadsheet"]["key"]
SHEET_NAME = "Backstock"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource(ttl=300)
def get_google_sheet():
    sa_info = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(sa_info, scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SPREADSHEET_KEY)
    return spreadsheet

def salvar_bulto_na_planilha(df_bulto):
    try:
        spreadsheet = get_google_sheet()
        try:
            sheet = spreadsheet.worksheet(SHEET_NAME)
        except gspread.WorksheetNotFound:
            sheet = spreadsheet.add_worksheet(title=SHEET_NAME, rows="1000", cols="20")
            sheet.append_row(list(df_bulto.columns))  # Cabeçalho
        # Se for a primeira linha, talvez precise garantir o cabeçalho
        existing_rows = sheet.get_all_values()
        if not existing_rows:
            sheet.append_row(list(df_bulto.columns))
        # Adiciona registros (exceto cabeçalho)
        rows = df_bulto.values.tolist()
        for row in rows:
            sheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar na planilha: {e}")
        return False

# --- RESTANTE DO APP ---
def hora_brasil():
    fuso_brasil = pytz.timezone('America/Sao_Paulo')
    return datetime.now(fuso_brasil).strftime("%d/%m/%Y %H:%M:%S")

def validar_usuario(codigo):
    try:
        url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQT66XECK150fz-NTRkNAEtlmt1sjSnfCHScgYB812JXd7UHs2JadldU5jOnQaZG3MDA95eJdgH5PZE/pub?output=csv"
        response = requests.get(url)
        response.encoding = 'utf-8'
        csv_data = StringIO(response.text)
        df = pd.read_csv(csv_data)
        if 'Criptografia' not in df.columns or 'Usuário' not in df.columns:
            st.error("Estrutura da planilha inválida. Verifique as colunas.")
            return None
        df['Criptografia'] = df['Criptografia'].astype(str).str.strip().str.lower()
        codigo = str(codigo).strip().lower()
        if codigo in df['Criptografia'].values:
            return df.loc[df['Criptografia'] == codigo, 'Usuário'].values[0]
        return None
    except Exception as e:
        st.error(f"Erro ao validar usuário: {str(e)}")
        return None

if "cadastros" not in st.session_state:
    st.session_state["cadastros"] = []
if "etapa" not in st.session_state:
    st.session_state.etapa = "bulto"  # bulto -> categoria -> sku

st.set_page_config(layout="wide")

st.markdown("""
    <style>
        .css-1omjdxh { color: white !important; }
        .big-font { font-size: 30px !important; text-align: center; margin: 10px 0; }
        .category-btn { height: 100px !important; font-size: 24px !important; margin: 10px 0; width: 100%; }
        .change-btn { background-color: #FFA500 !important; color: white !important; font-weight: bold; }
        .change-btn:hover { background-color: #FF8C00 !important; border-color: #FF8C00 !important; }
        .stButton>button { height: 60px !important; font-size: 20px !important; }
        .footer {
            position: fixed;
            bottom: 0;
            right: 10px;
            font-size: 12px;
            text-align: right;
            background-color: #9DD1F1;
            color: black;
            padding: 5px;
            z-index: 100;
        }
        .focused-input {
            border: 3px solid #4A90E2 !important;
            box-shadow: 0 0 10px #4A90E2 !important;
        }
    </style>
""", unsafe_allow_html=True)

def auto_focus_input(placeholder_text="Digite seu código de acesso..."):
    components.html(f"""
    <script>
    function focusUserInput() {{
        setTimeout(() => {{
            const inputs = Array.from(window.parent.document.querySelectorAll('input[type="text"]'));
            const targetInput = inputs.find(input => 
                input.value === "" && 
                (input.placeholder.includes("{placeholder_text}") || 
                 input.placeholder.includes("Bipe o SKU") ||
                 input.placeholder.includes("número do bulto"))
            );
            if (targetInput) {{
                targetInput.classList.add('focused-input');
                targetInput.focus();
                targetInput.addEventListener('blur', () => {{
                    targetInput.classList.remove('focused-input');
                }});
            }}
        }}, 100);
    }}
    focusUserInput();
    const observer = new MutationObserver(focusUserInput);
    observer.observe(window.parent.document.body, {{
        childList: true,
        subtree: true
    }});
    </script>
    """, height=0)

if "inicio" not in st.session_state:
    st.session_state["inicio"] = False      

if not st.session_state["inicio"]:
    st.title("SISTEMA DE CONTROLE DE BACKSTOCK")
    if st.button("Iniciar"):
        with st.spinner("Carregando o sistema..."):
            time.sleep(2)
        st.success("Sistema carregado com sucesso! Vamos para a tela de usuário.")
        time.sleep(1)
        st.session_state["inicio"] = True
        st.rerun()
    st.image("https://f.hellowork.com/media/123957/1440_960/IDLOGISTICSFRANCE_123957_63809226079153822430064462.jpeg", use_container_width=True)
    st.stop()

if "user_code" not in st.session_state or not st.session_state["user_code"]:
    st.session_state["user_code"] = ""
    st.session_state["user_name"] = ""

if not st.session_state["user_code"]:
    st.title("Cadastro Obrigatório para continuar o acesso")
    codigo_usuario = st.text_input("Digite seu código de acesso:", key="user_input", placeholder="Digite seu código de acesso...")
    auto_focus_input("Digite seu código de acesso...")
    if codigo_usuario.strip():
        with st.spinner("Validando código..."):
            nome_usuario = validar_usuario(codigo_usuario.strip())
        if nome_usuario:
            st.session_state["user_code"] = codigo_usuario.strip()
            st.session_state["user_name"] = nome_usuario
            st.success(f"Usuário validado: {nome_usuario}")
            time.sleep(1)
            st.rerun()
        else:
            st.error("❌ Código de acesso inválido. Por favor, tente novamente.")
    else:
        st.warning("Por favor, digite um código de acesso válido.")
    st.image("https://f.hellowork.com/media/123957/1440_960/IDLOGISTICSFRANCE_123957_63809226079153822430064462.jpeg", use_container_width=True)
    st.stop()

selecao = option_menu(
    menu_title="BACKSTOCK",
    options=["Cadastro Bulto", "Tabela", "Home"],
    icons=["box", "table", "house"],
    menu_icon="cast",
    orientation="horizontal"
)

if selecao == "Home":
    st.session_state["inicio"] = False
    st.session_state["user_code"] = ""
    st.session_state["user_name"] = ""
    st.session_state["bulto_cadastrado"] = False
    st.session_state.etapa = "bulto"
    st.rerun()

if selecao == "Cadastro Bulto":
    if st.session_state.etapa == "bulto":
        st.markdown("<h1 style='color:black; text-align: center;'>Cadastro de Bultos</h1>", unsafe_allow_html=True)
        st.markdown("<h2 style='color:black; text-align: center;'>Digite o número do bulto</h2>", unsafe_allow_html=True)
        bulto = st.text_input("", key="bulto_input", placeholder="Digite o número do bulto...")
        auto_focus_input()
        if bulto:
            st.session_state["bulto_numero"] = bulto
            st.session_state["bulto_cadastrado"] = True
            st.session_state.etapa = "categoria"
            st.session_state["peca_reset_count"] = 0
            st.rerun()
    elif st.session_state.etapa == "categoria":
        st.markdown("<h1 style='color:black; text-align: center;'>Selecione a Categoria</h1>", unsafe_allow_html=True)
        st.markdown(f"<div class='big-font'>Bulto: {st.session_state['bulto_numero']}</div>", unsafe_allow_html=True)
        categorias = ["Ubicação", "Limpeza", "Tara Maior", "Costura", "Reetiquetagem"]
        cols = st.columns(2)
        for i, categoria in enumerate(categorias):
            col = cols[i % 2]
            with col:
                if st.button(categoria, key=f"cat_{categoria}", use_container_width=True):
                    st.session_state["categoria_selecionada"] = categoria
                    st.session_state.etapa = "sku"
                    st.rerun()
    elif st.session_state.etapa == "sku":
        st.markdown("<h1 style='color:black; text-align: center;'>Cadastro de Peças</h1>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"<div class='big-font'>Usuário: {st.session_state['user_name']}</div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='big-font'>Bulto: {st.session_state['bulto_numero']}</div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div class='big-font'>Categoria: {st.session_state['categoria_selecionada']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='big-font'>Peças cadastradas: {st.session_state.get('peca_reset_count', 0)}</div>", unsafe_allow_html=True)
        if st.button("↩️ Mudar Categoria", key="mudar_categoria", use_container_width=True, type="secondary"):
            st.session_state.etapa = "categoria"
            st.rerun()
        unique_key = f"sku_input_{st.session_state.get('peca_reset_count', 0)}"
        sku = st.text_input("Digite o SKU:", key=unique_key, placeholder="Bipe o SKU e pressione Enter...")
        auto_focus_input()
        if sku:
            novo_cadastro = {
                "Usuário": st.session_state["user_name"],
                "Bulto": st.session_state["bulto_numero"],
                "SKU": sku,
                "Categoria": st.session_state["categoria_selecionada"],
                "Data/Hora": hora_brasil()
            }
            st.session_state["cadastros"].append(novo_cadastro)
            st.success(f"Peça '{sku}' cadastrada com sucesso!")
            st.session_state["peca_reset_count"] = st.session_state.get("peca_reset_count", 0) + 1
            st.rerun()
        if st.button("✅ Finalizar Bulto", key="finalizar_bulto", use_container_width=True, type="primary"):
            if st.session_state.get("peca_reset_count", 0) > 0:
                bulto_atual = st.session_state["bulto_numero"]
                df_cadastros = pd.DataFrame([c for c in st.session_state["cadastros"] if c["Bulto"] == bulto_atual])
                if not df_cadastros.empty:
                    sucesso = salvar_bulto_na_planilha(df_cadastros)
                    if sucesso:
                        st.success("✅ Bulto finalizado e salvo na planilha com sucesso!")
                    else:
                        st.error("❌ Erro ao salvar o bulto na planilha.")
                else:
                    st.warning("⚠️ Nenhuma peça cadastrada neste bulto para envio.")
            else:
                st.warning("⚠️ Nenhuma peça cadastrada neste bulto.")
            st.session_state["bulto_cadastrado"] = False
            st.session_state["peca_reset_count"] = 0
            st.session_state.etapa = "bulto"
            st.rerun()

elif selecao == "Tabela":
    st.markdown("<h1 style='color:black; text-align: center;'>Tabela de Peças Cadastradas</h1>", unsafe_allow_html=True)
    if st.session_state["cadastros"]:
        df_cadastros = pd.DataFrame(st.session_state["cadastros"])
        st.dataframe(df_cadastros, use_container_width=True)
        if st.button("🧹 Limpar todos os registros", type="secondary", use_container_width=True):
            st.session_state["cadastros"] = []
            st.success("Todos os registros foram limpos!")
            st.rerun()
    else:
        st.info("Nenhuma peça cadastrada até o momento.")

st.markdown("""
    <div class="footer">
        Copyright © 2025 Direitos Autorais Desenvolvedor Rogério Ferreira
    </div>
""", unsafe_allow_html=True)

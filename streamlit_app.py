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

@st.cache_data(ttl=120, show_spinner="Carregando registros da planilha...")
def load_backstock_data():
    try:
        sheet = get_google_sheet().worksheet(SHEET_NAME)
        data = sheet.get_all_records()
        if data:
            return pd.DataFrame(data)
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar dados da planilha: {e}")
        return pd.DataFrame()

def salvar_bulto_na_planilha(df_bulto):
    # Garante que só as colunas corretas vão para a planilha
    expected_columns = ["Usuário", "Bulto", "SKU", "Categoria", "Data/Hora"]
    df_bulto = df_bulto.loc[:, expected_columns]
    try:
        spreadsheet = get_google_sheet()
        try:
            sheet = spreadsheet.worksheet(SHEET_NAME)
        except gspread.WorksheetNotFound:
            sheet = spreadsheet.add_worksheet(title=SHEET_NAME, rows="1000", cols="20")
            sheet.append_row(expected_columns)  # Cabeçalho
        existing_rows = sheet.get_all_values()
        if not existing_rows:
            sheet.append_row(expected_columns)
        rows = df_bulto.values.tolist()
        for row in rows:
            sheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar na planilha: {e}")
        return False

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

# ------ ID LOGISTICS DESIGN: CUSTOM CSS ------
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
        .enviando-msg-idlog {
            background: linear-gradient(90deg, #003366 0%, #ffffff 60%, #d52b1e 100%);
            color: #003366;
            border-radius: 12px;
            border: 4px solid #003366;
            font-size: 2.2em;
            font-weight: bold;
            text-align: center;
            padding: 40px 18px 40px 18px;
            margin: 30px 0 30px 0;
            box-shadow: 0 4px 18px 0 rgba(0,0,0,0.07);
            letter-spacing: 2px;
            position: relative;
        }
        .enviando-msg-idlog::before {
            content: '';
            display: inline-block;
            background: url('https://www.id-logistics.com/wp-content/themes/idl-theme/assets/img/logo-id-logistics.svg') no-repeat center/90px;
            width: 90px;
            height: 36px;
            position: absolute;
            top: 16px;
            left: 50%;
            transform: translateX(-50%);
        }
        @media (max-width: 600px) {
            .enviando-msg-idlog {
                font-size: 1.4em;
                padding: 24px 8px;
            }
            .enviando-msg-idlog::before {
                width: 60px;
                height: 24px;
                top: 10px;
            }
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
    codigo_usuario = st.text_input(
        "Código de acesso", 
        key="user_input", 
        placeholder="Digite seu código de acesso...",
        label_visibility="collapsed"
    )
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
    options=["Cadastro Bulto", "Tabela", "Visualizar Planilha", "Sair"],
    icons=["box", "table", "eye", "house"],
    menu_icon="cast",
    orientation="horizontal"
)

if selecao == "Sair":
    st.session_state["inicio"] = False
    st.session_state["user_code"] = ""
    st.session_state["user_name"] = ""
    st.session_state["bulto_cadastrado"] = False
    st.session_state.etapa = "bulto"
    st.session_state["finalizar_bulto_disabled"] = False
    st.session_state["finalizar_bulto_aguardando"] = False
    st.rerun()

if selecao == "Cadastro Bulto":
    if (
        "finalizar_bulto_disabled" not in st.session_state
        or st.session_state.get("reset_finalizar_bulto", False)
    ):
        st.session_state["finalizar_bulto_disabled"] = False
        st.session_state["reset_finalizar_bulto"] = False
    if "finalizar_bulto_aguardando" not in st.session_state:
        st.session_state["finalizar_bulto_aguardando"] = False

    if st.session_state.etapa == "bulto":
        st.markdown("<h1 style='color:black; text-align: center;'>Cadastro de Bultos</h1>", unsafe_allow_html=True)
        st.markdown("<h2 style='color:black; text-align: center;'>Digite o número do bulto</h2>", unsafe_allow_html=True)
        bulto = st.text_input(
            "Número do bulto", 
            key="bulto_input", 
            placeholder="Digite o número do bulto...",
            label_visibility="collapsed"
        )
        auto_focus_input()
        if bulto:
            st.session_state["bulto_numero"] = bulto
            st.session_state["bulto_cadastrado"] = True
            st.session_state.etapa = "categoria"
            st.session_state["peca_reset_count"] = 0
            st.session_state["reset_finalizar_bulto"] = True
            st.rerun()
    elif st.session_state.etapa == "categoria":
        st.markdown("<h1 style='color:black; text-align: center;'>Selecione a Categoria</h1>", unsafe_allow_html=True)
        st.markdown(f"<div class='big-font'>Bulto: {st.session_state['bulto_numero']}</div>", unsafe_allow_html=True)
        categorias = [
            "Ubicação",
            "Limpeza",
            "Tara maior - Não recuperável",
            "Tara maior - sem SKU Interno",
            "Costura",
            "Reetiquetagem"
        ]
        cols = st.columns(2)
        for i, categoria in enumerate(categorias):
            col = cols[i % 2]
            with col:
                if st.button(categoria, key=f"cat_{categoria}", use_container_width=True):
                    st.session_state["categoria_selecionada"] = categoria
                    # Se for a categoria especial, pula para etapa especial
                    if categoria == "Tara maior - sem SKU Interno":
                        st.session_state.etapa = "quantidade"
                    else:
                        st.session_state.etapa = "sku"
                    st.session_state["reset_finalizar_bulto"] = True
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
        sku = st.text_input(
            "SKU", 
            key=unique_key, 
            placeholder="Bipe o SKU e pressione Enter...",
            label_visibility="collapsed"
        )
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

        def bloquear_finalizar_bulto():
            st.session_state["finalizar_bulto_disabled"] = True
            st.session_state["finalizar_bulto_aguardando"] = True

        st.button(
            "✅ Finalizar Bulto",
            key="finalizar_bulto",
            use_container_width=True,
            type="primary",
            disabled=st.session_state["finalizar_bulto_disabled"],
            on_click=bloquear_finalizar_bulto
        )

        if st.session_state.get("finalizar_bulto_aguardando", False):
            st.markdown('<div class="enviando-msg-idlog">Finalizando Bulto...<br>Por favor, aguarde!</div>', unsafe_allow_html=True)
            with st.spinner("Salvando bulto na planilha, aguarde..."):
                time.sleep(0.7)
                if st.session_state.get("peca_reset_count", 0) > 0:
                    bulto_atual = st.session_state["bulto_numero"]
                    df_cadastros = pd.DataFrame([c for c in st.session_state["cadastros"] if c["Bulto"] == bulto_atual])
                    expected_columns = ["Usuário", "Bulto", "SKU", "Categoria", "Data/Hora"]
                    if "Quantidade" in df_cadastros.columns:
                        expected_columns.insert(4, "Quantidade")
                    df_cadastros = df_cadastros.loc[:, expected_columns]
                    if not df_cadastros.empty:
                        sucesso = salvar_bulto_na_planilha(df_cadastros)
                        if sucesso:
                            st.success("✅ Bulto finalizado e salvo na planilha com sucesso!")
                            st.session_state["cadastros"] = []
                        else:
                            st.error("❌ Erro ao salvar o bulto na planilha.")
                    else:
                        st.warning("⚠️ Nenhuma peça cadastrada neste bulto para envio.")
                else:
                    st.warning("⚠️ Nenhuma peça cadastrada neste bulto.")
                st.session_state["bulto_cadastrado"] = False
                st.session_state["peca_reset_count"] = 0
                st.session_state.etapa = "bulto"
                st.session_state["finalizar_bulto_aguardando"] = False
            st.rerun()
    elif st.session_state.etapa == "quantidade":
        # Só para a categoria "Tara maior - sem SKU Interno"
        if st.session_state.get("categoria_selecionada", "") == "Tara maior - sem SKU Interno":
            st.markdown("<h1 style='color:black; text-align: center;'>Cadastro de Peças - Tara maior sem SKU Interno</h1>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"<div class='big-font'>Usuário: {st.session_state['user_name']}</div>", unsafe_allow_html=True)
            with col2:
                st.markdown(f"<div class='big-font'>Bulto: {st.session_state['bulto_numero']}</div>", unsafe_allow_html=True)
            with col3:
                st.markdown(f"<div class='big-font'>Categoria: {st.session_state['categoria_selecionada']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='big-font'>Peças cadastradas: {st.session_state.get('peca_reset_count', 0)}</div>", unsafe_allow_html=True)
            if st.button("↩️ Mudar Categoria", key="mudar_categoria_qtd", use_container_width=True, type="secondary"):
                st.session_state.etapa = "categoria"
                st.rerun()
            unique_key = f"qtd_input_{st.session_state.get('peca_reset_count', 0)}"
            quantidade = st.number_input(
                "Quantidade de peças",
                min_value=1,
                step=1,
                key=unique_key,
                placeholder="Digite a quantidade de peças...",
            )
            auto_focus_input("Digite a quantidade de peças...")

            def bloquear_finalizar_bulto_tara_maior():
                st.session_state["finalizar_bulto_disabled"] = True
                st.session_state["finalizar_bulto_aguardando_3000000000000"] = True

            st.button(
                "✅ Finalizar Bulto",
                key="finalizar_bulto_sku_3000000000000",
                use_container_width=True,
                type="primary",
                disabled=st.session_state.get("finalizar_bulto_disabled", False),
                on_click=bloquear_finalizar_bulto_tara_maior
            )

            # Fluxo para finalizar bulto com SKU '3000000000000' (quantidade de linhas igual ao digitado)
            if st.session_state.get("finalizar_bulto_aguardando_3000000000000", False):
                st.markdown('<div class="enviando-msg-idlog">Finalizando Bulto com SKU 3000000000000...<br>Por favor, aguarde!</div>', unsafe_allow_html=True)
                with st.spinner("Salvando bulto na planilha, aguarde..."):
                    time.sleep(0.7)
                    if quantidade and quantidade > 0:
                        bulto_atual = st.session_state["bulto_numero"]
                        data_hora = hora_brasil()
                        linhas = []
                        for i in range(int(quantidade)):
                            cadastro_3000000000000 = {
                                "Usuário": st.session_state["user_name"],
                                "Bulto": bulto_atual,
                                "SKU": "3000000000000",
                                "Categoria": st.session_state["categoria_selecionada"],
                                "Data/Hora": data_hora
                            }
                            linhas.append(cadastro_3000000000000)
                        df_cadastros = pd.DataFrame(linhas)
                        expected_columns = ["Usuário", "Bulto", "SKU", "Categoria", "Data/Hora"]
                        df_cadastros = df_cadastros.loc[:, expected_columns]
                        sucesso = salvar_bulto_na_planilha(df_cadastros)
                        if sucesso:
                            st.success(f"✅ Bulto finalizado e salvo na planilha com {quantidade} linhas (SKU 3000000000000)!")
                            st.session_state["cadastros"] = []
                        else:
                            st.error("❌ Erro ao salvar o bulto na planilha.")
                    else:
                        st.warning("⚠️ Nenhuma quantidade informada para envio.")
                    st.session_state["bulto_cadastrado"] = False
                    st.session_state["peca_reset_count"] = 0
                    st.session_state.etapa = "bulto"
                    st.session_state["finalizar_bulto_aguardando_3000000000000"] = False
                    st.session_state["finalizar_bulto_disabled"] = False
                st.rerun()
        else:
            # Caso no futuro outras categorias usem essa etapa,
            # pode seguir o fluxo padrão (se houver).
            st.markdown("Categoria inválida para etapa de quantidade.", unsafe_allow_html=True)
            if st.button("↩️ Voltar", key="voltar_quantidade_erro"):
                st.session_state.etapa = "categoria"
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

elif selecao == "Visualizar Planilha":
    st.header("📋 Visualização dos Registros da Planilha Backstock")
    if st.button("🔄 Atualizar Dados da Planilha"):
        load_backstock_data.clear()
        st.toast("Dados da planilha atualizados!", icon="🔄")
    df = load_backstock_data()
    if not df.empty:
        for col in ["Bulto", "SKU"]:
            if col in df.columns:
                df[col] = df[col].astype(str)
        if "Data/Hora" in df.columns:
            df["Data/Hora"] = df["Data/Hora"].astype(str)
            df = df[df["Data/Hora"].str.len() > 5]
            df["Data/Hora_dt"] = pd.to_datetime(df["Data/Hora"], dayfirst=True, errors="coerce")
            df = df[~df["Data/Hora_dt"].isna()]
            df = df.sort_values("Data/Hora_dt", ascending=False)
            df = df.drop(columns=["Data/Hora_dt"])
        st.subheader("Filtros")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            setor_filtro = st.selectbox("Bulto:", ["Todos"] + sorted(df['Bulto'].dropna().unique()))
        with col2:
            categoria_filtro = st.selectbox("Categoria:", ["Todas"] + sorted(df['Categoria'].dropna().unique()))
        with col3:
            usuario_filtro = st.selectbox("Usuário:", ["Todos"] + sorted(df['Usuário'].dropna().unique()))
        with col4:
            data_filtro = st.date_input("Data:", datetime.now())
        if setor_filtro != "Todos":
            df = df[df['Bulto'] == setor_filtro]
        if categoria_filtro != "Todas":
            df = df[df['Categoria'] == categoria_filtro]
        if usuario_filtro != "Todos":
            df = df[df['Usuário'] == usuario_filtro]
        if data_filtro:
            df = df[pd.to_datetime(df['Data/Hora'], dayfirst=True, errors="coerce").dt.date == data_filtro]
        st.dataframe(df, use_container_width=True)
        st.subheader("📊 Estatísticas")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total de Registros", len(df))
        with col2:
            st.metric("Bultos Diferentes", df['Bulto'].nunique())
        with col3:
            st.metric("Categorias", df['Categoria'].nunique())
        with col4:
            st.metric("Usuários", df['Usuário'].nunique())
        tab1, tab2, tab3 = st.tabs(["Bultos", "Categorias", "Usuários"])
        with tab1:
            st.bar_chart(df['Bulto'].value_counts())
        with tab2:
            st.bar_chart(df['Categoria'].value_counts())
        with tab3:
            st.bar_chart(df['Usuário'].value_counts().head(5))
    else:
        st.info("Nenhum registro encontrado na planilha.")

st.markdown("""
    <div class="footer">
        Copyright © 2025 Direitos Autorais Desenvolvedores Rogério Ferreira e Kauê Oliveira
    </div>
""", unsafe_allow_html=True)

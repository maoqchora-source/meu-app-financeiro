import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURAÇÕES DE LAYOUT E CONEXÃO
st.set_page_config(page_title="Planejamento Financeiro", layout="wide", initial_sidebar_state="collapsed")

# SUBSTITUA PELO SEU LINK DO GOOGLE SHEETS
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/SEU_ID_AQUI/edit#gid=0"

# Criar a conexão com o Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CORES E TEMA ---
modo_escuro = st.toggle("🌙 Modo Escuro")
COR_PRIMARIA = "#2d6a4f"

if modo_escuro:
    COR_FUNDO = "#1c1c1c"
    COR_TEXTO = "#f1f1f1"
    GRADIENTE = "linear-gradient(135deg, #1c1c1c 0%, #2d2d2d 100%)"
    CARD_BG = "#2c2c2c"
    CARD_TEXT = "#f1f1f1"
    PLOT_THEME = "plotly_dark"
else:
    COR_FUNDO = "#f8f9fa"
    COR_TEXTO = "#2c3e50"
    GRADIENTE = "linear-gradient(135deg, #f8f9fa 0%, #e9f5ec 100%)"
    CARD_BG = "white"
    CARD_TEXT = "#2c3e50"
    PLOT_THEME = "plotly_white"

# CSS DINÂMICO
st.markdown(f"""
    <style>
    .stApp {{ background: {GRADIENTE}; }}
    h1 {{
      background: linear-gradient(90deg, {COR_PRIMARIA}, #40916c);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      font-weight: 900;
      text-align: center;
    }}
    .card {{
        background-color: {CARD_BG};
        color: {CARD_TEXT};
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.1);
        text-align: center;
        margin-bottom: 10px;
    }}
    /* Estilo das Abas */
    .stTabs [data-baseweb="tab-list"] {{
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 8px;
    }}
    .stTabs [data-baseweb="tab"] {{
        background-color: {CARD_BG};
        color: {CARD_TEXT};
        border-radius: 12px;
        height: 60px;
        font-weight: bold !important;
        border: 1px solid rgba(0,0,0,0.1);
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {COR_PRIMARIA} !important;
        color: white !important;
    }}
    /* Botão Gravar Dados Fixo */
    div[data-testid="stVerticalBlock"] > div:has(button[key="btn_gravar"]) {{
        position: fixed;
        bottom: 20px;
        left: 5%;
        right: 5%;
        z-index: 999;
    }}
    .stButton>button[key="btn_gravar"] {{
        width: 90vw !important;
        height: 55px !important;
        border-radius: 15px !important;
        background-color: {COR_PRIMARIA} !important;
        color: white !important;
        font-weight: 900 !important;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.3) !important;
    }}
    </style>
""", unsafe_allow_html=True)

# 2. FUNÇÕES DE DADOS (GOOGLE SHEETS)
def carregar_dados(aba, colunas):
    try:
        df = conn.read(spreadsheet=URL_PLANILHA, worksheet=aba, ttl="0")
        if df is None or df.empty:
            return pd.DataFrame(columns=colunas)
        if 'Data' in df.columns:
            df['Data'] = pd.to_datetime(df['Data']).dt.date
        return df.reindex(columns=colunas)
    except:
        return pd.DataFrame(columns=colunas)

def salvar_dados(df, aba):
    conn.update(spreadsheet=URL_PLANILHA, worksheet=aba, data=df)
    st.cache_data.clear()

# Inicialização dos DataFrames
cols_trans = ['Data', 'Tipo', 'Categoria', 'Descricao', 'Valor']
cols_inv = ['Data', 'Tipo_Ativo', 'Descricao', 'Valor_Aplicado', 'Taxa_Anual', 'Meta_Destino']
cols_metas = ['Nome_Meta', 'Valor_Objetivo']

df_transacoes = carregar_dados('vendas', cols_trans)
df_invest = carregar_dados('investimentos', cols_inv)
df_metas = carregar_dados('metas', cols_metas)

# Saldo para aporte (Simulado via session_state para esta sessão)
if 'saldo_para_aportar' not in st.session_state:
    st.session_state.saldo_para_aportar = 0.0

# 3. JANELA MODAL (DIALOG)
@st.dialog("📝 **NOVO LANÇAMENTO**")
def cadastrar_dialog():
    tipo = st.selectbox("**Operação**", ["Receita", "Gasto"])
    cat = st.selectbox("**Categoria**", ["Trabalho", "Fixo", "Variável", "Lazer", "Saúde", "Investimento"])
    desc = st.text_input("**Descrição**")
    valor_in = st.number_input("**Valor R$**", min_value=0.0)
    data_in = st.date_input("**Data**")
    perc_inv = 0
    if tipo == "Receita":
        perc_inv = st.slider("**Investir (%)**", 0, 100, 0)
    
    if st.button("**CONFIRMAR E SALVAR**"):
        if valor_in > 0:
            global df_transacoes
            nova = pd.DataFrame([[data_in, tipo, cat, desc, valor_in]], columns=cols_trans)
            df_atualizado = pd.concat([df_transacoes, nova], ignore_index=True)
            
            if tipo == "Receita" and perc_inv > 0:
                v_inv = (valor_in * perc_inv) / 100
                ajuste = pd.DataFrame([[data_in, "Gasto", "Investimento", f"Reserva: {desc}", v_inv]], columns=cols_trans)
                df_atualizado = pd.concat([df_atualizado, ajuste], ignore_index=True)
                st.session_state.saldo_para_aportar += v_inv
            
            salvar_dados(df_atualizado, 'vendas')
            st.success("**DADOS GRAVADOS NO GOOGLE SHEETS!**")
            st.rerun()

# 4. PROCESSAMENTO
if not df_invest.empty:
    def calc_atual(row):
        try:
            d = (date.today() - pd.to_datetime(row['Data']).date()).days
            if d <= 0: return row['Valor_Aplicado']
            return row['Valor_Aplicado'] * (1 + ((row['Taxa_Anual']/100)/365))**d
        except: return row['Valor_Aplicado']
    df_invest['Valor_Atualizado'] = df_invest.apply(calc_atual, axis=1)
    total_inv = df_invest['Valor_Atualizado'].sum()
else: total_inv = 0

rec = df_transacoes[df_transacoes['Tipo'] == 'Receita']['Valor'].sum()
gas = df_transacoes[df_transacoes['Tipo'] == 'Gasto']['Valor'].sum()
saldo_cc = rec - gas

# 5. EXIBIÇÃO PRINCIPAL
st.markdown("<h1>💼 PLANEJAMENTO FINANCEIRO</h1>", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    st.markdown(f"<div class='card'><h4>💰 Disponível</h4><h2>R$ {saldo_cc:,.2f}</h2></div>", unsafe_allow_html=True)
with col2:
    st.markdown(f"<div class='card'><h4>📈 Investido</h4><h2>R$ {total_inv:,.2f}</h2></div>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 DASH", "📈 CARTEIRA", "🎯 METAS", "📅 ANUAL", "⚙️ AJUSTES"])

with tab1:
    st.markdown("### **DISTRIBUIÇÃO DE GASTOS**")
    if not df_transacoes.empty:
        df_g = df_transacoes[(df_transacoes['Tipo']=='Gasto') & (df_transacoes['Categoria']!='Investimento')]
        if not df_g.empty:
            fig = px.pie(df_g, values='Valor', names='Categoria', hole=0.5, color_discrete_sequence=['#2d6a4f', '#40916c', '#74c69d', '#95d5b2'])
            fig.update_layout(template=PLOT_THEME, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
    else: st.info("**NENHUM DADO REGISTRADO AINDA.**")

with tab2:
    st.subheader("🏦 Carteira de Ativos")
    if st.session_state.saldo_para_aportar > 0:
        st.warning(f"💰 Saldo para Aplicar: **R$ {st.session_state.saldo_para_aportar:,.2f}**")
        col_a, col_b = st.columns(2)
        t_at = col_a.selectbox("Tipo:", ["CDI", "LCA", "FIIs", "Ações"])
        tx_at = col_b.number_input("Taxa Anual %", value=12.0)
        nm_at = st.text_input("Nome do Papel")
        m_dest = st.selectbox("Meta:", df_metas['Nome_Meta'].tolist() if not df_metas.empty else ["Geral"])
        
        if st.button("Confirmar Aplicação"):
            novo = pd.DataFrame([[date.today(), t_at, nm_at, st.session_state.saldo_para_aportar, tx_at, m_dest]], columns=cols_inv)
            df_inv_novo = pd.concat([df_invest, novo], ignore_index=True)
            salvar_dados(df_inv_novo, 'investimentos')
            st.session_state.saldo_para_aportar = 0.0
            st.rerun()
    
    st.dataframe(df_invest, use_container_width=True)

with tab3:
    st.subheader("🚩 Objetivos")
    with st.expander("➕ Nova Meta"):
        n_meta = st.text_input("Nome da Meta")
        v_meta = st.number_input("Valor Alvo", min_value=1.0)
        if st.button("Criar Meta"):
            nova_m = pd.DataFrame([[n_meta, v_meta]], columns=cols_metas)
            df_metas_novo = pd.concat([df_metas, nova_m], ignore_index=True)
            salvar_dados(df_metas_novo, 'metas')
            st.rerun()

    if not df_metas.empty:
        for i, m in df_metas.iterrows():
            acum = df_invest[df_invest['Meta_Destino'] == m['Nome_Meta']]['Valor_Atualizado'].sum() if not df_invest.empty else 0
            st.write(f"**{m['Nome_Meta']}**")
            st.progress(min(acum / m['Valor_Objetivo'], 1.0))

with tab4:
    if not df_transacoes.empty:
        df_transacoes['Data'] = pd.to_datetime(df_transacoes['Data'])
        df_transacoes['Mes'] = df_transacoes['Data'].dt.strftime('%b/%Y')
        df_mensal = df_transacoes.groupby(['Mes', 'Tipo'])['Valor'].sum().reset_index()
        fig_anual = px.bar(df_mensal, x='Mes', y='Valor', color='Tipo', barmode='group', color_discrete_map={'Receita':COR_PRIMARIA, 'Gasto':'#adb5bd'})
        fig_anual.update_layout(template=PLOT_THEME, paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_anual, use_container_width=True)

with tab5:
    st.subheader("⚙️ Ajustes Planilha")
    st.write("Edite os dados diretamente abaixo:")
    df_edit = st.data_editor(df_transacoes, num_rows="dynamic", use_container_width=True)
    if st.button("Salvar Alterações na Planilha"):
        salvar_dados(df_edit, 'vendas')
        st.rerun()

# 6. BOTÃO PRINCIPAL "GRAVAR DADOS"
if st.button("GRAVAR DADOS", key="btn_gravar"):
    cadastrar_dialog()

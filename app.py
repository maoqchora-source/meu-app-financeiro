import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURAÇÕES DE LAYOUT E CONEXÃO
st.set_page_config(page_title="Planejamento Financeiro", layout="wide", initial_sidebar_state="collapsed")

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1epf2H2ZjrmmXrS2OV-8W3P7LC7dp2FKJTHumWNevVeo/edit#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

# Limpeza de cache para atualização em tempo real
if 'init' not in st.session_state:
    st.cache_data.clear()
    st.session_state.init = True

# --- CORES E TEMA (RESTALRADO) ---
modo_escuro = st.toggle("🌙 Modo Escuro")
COR_PRIMARIA = "#2d6a4f"

if modo_escuro:
    GRADIENTE = "linear-gradient(135deg, #1c1c1c 0%, #2d2d2d 100%)"
    CARD_BG = "#2c2c2c"
    CARD_TEXT = "#f1f1f1"
    PLOT_THEME = "plotly_dark"
else:
    GRADIENTE = "linear-gradient(135deg, #f8f9fa 0%, #e9f5ec 100%)"
    CARD_BG = "white"
    CARD_TEXT = "#2c3e50"
    PLOT_THEME = "plotly_white"

# CSS ORIGINAL (RESTALRADO)
st.markdown(f"""
    <style>
    .stApp {{ background: {GRADIENTE}; }}
    h1 {{
      background: linear-gradient(90deg, {COR_PRIMARIA}, #40916c);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      font-weight: 900;
      text-align: center;
      margin-bottom: 20px;
    }}
    .card {{
        background-color: {CARD_BG};
        color: {CARD_TEXT};
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.1);
        text-align: center;
        margin-bottom: 15px;
    }}
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
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {COR_PRIMARIA} !important;
        color: white !important;
    }}
    </style>
""", unsafe_allow_html=True)

# 2. FUNÇÕES DE DADOS
def carregar_dados(aba, colunas):
    try:
        df = conn.read(spreadsheet=URL_PLANILHA, worksheet=aba, ttl="0")
        if df is None or df.empty: return pd.DataFrame(columns=colunas)
        if 'Data' in df.columns:
            df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        return df
    except: return pd.DataFrame(columns=colunas)

def salvar_dados(df, aba):
    conn.update(spreadsheet=URL_PLANILHA, worksheet=aba, data=df)
    st.cache_data.clear()

def obter_saldo_nuvem():
    try:
        df_conf = conn.read(spreadsheet=URL_PLANILHA, worksheet='config', ttl="0")
        return float(df_conf.iloc[0, 0])
    except: return 0.0

def salvar_saldo_nuvem(valor):
    df_conf = pd.DataFrame([{"saldo_aporte": float(valor)}])
    conn.update(spreadsheet=URL_PLANILHA, worksheet='config', data=df_conf)
    st.cache_data.clear()

# Inicialização
cols_trans = ['Data', 'Tipo', 'Categoria', 'Descricao', 'Valor']
cols_inv = ['Data', 'Tipo_Ativo', 'Descricao', 'Valor_Aplicado', 'Taxa_Anual', 'Meta_Destino']
cols_metas = ['Nome_Meta', 'Valor_Objetivo']

df_transacoes = carregar_dados('vendas', cols_trans)
df_invest = carregar_dados('investimentos', cols_inv)
df_metas = carregar_dados('metas', cols_metas)
saldo_reservado = obter_saldo_nuvem()

# 3. CÁLCULOS (BLINDADOS CONTRA ERROS DE TIPO)
try:
    # Garante que os valores são numéricos, substituindo erros por 0
    df_transacoes['Valor'] = pd.to_numeric(df_transacoes['Valor'], errors='coerce').fillna(0)
    
    total_rec = float(df_transacoes[df_transacoes['Tipo'] == 'Receita']['Valor'].sum())
    total_gas = float(df_transacoes[df_transacoes['Tipo'] == 'Gasto']['Valor'].sum())
    
    # Garante que o saldo reservado é um número único (float)
    val_reserva = float(saldo_reservado) if isinstance(saldo_reservado, (int, float)) else 0.0
    
    # CÁLCULO REAL: Entradas - Saídas - O que foi guardado para investir
    saldo_cc = total_rec - total_gas - val_reserva
    
    if not df_invest.empty:
        df_invest['Valor_Aplicado'] = pd.to_numeric(df_invest['Valor_Aplicado'], errors='coerce').fillna(0)
        total_inv = float(df_invest['Valor_Aplicado'].sum())
    else:
        total_inv = 0.0
except Exception as e:
    st.error(f"Erro no cálculo: {e}")
    saldo_cc = 0.0
    total_inv = 0.0
# 4. EXIBIÇÃO PRINCIPAL
st.markdown("<h1>💼 FINANCEIRO</h1>", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    st.markdown(f"<div class='card'><h5>💰 Conta</h5><h2>R$ {saldo_cc:,.2f}</h2></div>", unsafe_allow_html=True)
with col2:
    st.markdown(f"<div class='card'><h5>📈 Investido</h5><h2>R$ {total_inv:,.2f}</h2></div>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 DASH", "📈 CARTEIRA", "🎯 METAS", "📅 ANUAL", "⚙️ AJUSTES"])

with tab1:
    st.markdown("### **DISTRIBUIÇÃO DE GASTOS**")
    df_g = df_transacoes[df_transacoes['Tipo'] == 'Gasto']
    if not df_g.empty:
        fig = px.pie(df_g, values='Valor', names='Categoria', hole=0.5, color_discrete_sequence=px.colors.sequential.Greens_r)
        fig.update_layout(template=PLOT_THEME, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
    else: st.info("Sem dados de gastos.")

with tab2:
    st.subheader("🏦 Carteira")
    if saldo_reservado > 0:
        st.warning(f"💰 Reservado para Aplicar: **R$ {saldo_reservado:,.2f}**")
        with st.expander("Confirmar Aplicação"):
            t_at = st.selectbox("Tipo:", ["CDI", "LCA", "FIIs", "Ações"])
            nm_at = st.text_input("Papel")
            tx_at = st.number_input("Taxa Anual %", value=12.0)
            m_dest = st.selectbox("Meta:", df_metas['Nome_Meta'].tolist() if not df_metas.empty else ["Geral"])
            if st.button("Gravar Investimento"):
                novo = pd.DataFrame([[str(date.today()), t_at, nm_at, saldo_reservado, tx_at, m_dest]], columns=cols_inv)
                salvar_dados(pd.concat([df_invest, novo], ignore_index=True), 'investimentos')
                salvar_saldo_nuvem(0.0) # ZERA O SALDO NA PLANILHA
                st.rerun()
    st.dataframe(df_invest, use_container_width=True)

with tab3:
    st.subheader("🚩 Metas")
    if not df_metas.empty:
        for _, m in df_metas.iterrows():
            acum = df_invest[df_invest['Meta_Destino'] == m['Nome_Meta']]['Valor_Aplicado'].sum() if not df_invest.empty else 0
            st.write(f"**{m['Nome_Meta']}**")
            st.progress(min(acum / m['Valor_Objetivo'], 1.0))
    with st.expander("Nova Meta"):
        n_meta = st.text_input("Nome")
        v_meta = st.number_input("Alvo", min_value=1.0)
        if st.button("Criar"):
            salvar_dados(pd.concat([df_metas, pd.DataFrame([[n_meta, v_meta]], columns=cols_metas)], ignore_index=True), 'metas')
            st.rerun()

with tab4:
    st.subheader("Evolução Mensal")
    if not df_transacoes.empty:
        df_anual = df_transacoes.copy().dropna(subset=['Data'])
        df_anual['Mes'] = df_anual['Data'].dt.strftime('%m/%Y')
        df_m = df_anual.groupby(['Mes', 'Tipo'])['Valor'].sum().reset_index()
        fig_bar = px.bar(df_m, x='Mes', y='Valor', color='Tipo', barmode='group', color_discrete_map={'Receita':'#2d6a4f', 'Gasto':'#bc4749'})
        fig_bar.update_layout(template=PLOT_THEME, paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_bar, use_container_width=True)

with tab5:
    st.subheader("⚙️ Central de Controle")
    ed_v = st.data_editor(df_transacoes, num_rows="dynamic", use_container_width=True)
    if st.button("Salvar Tudo"):
        salvar_dados(ed_v, 'vendas')
        st.rerun()
    st.divider()
    if st.button("LIMPAR TUDO", type="primary"):
        salvar_dados(pd.DataFrame(columns=cols_trans), 'vendas')
        salvar_dados(pd.DataFrame(columns=cols_inv), 'investimentos')
        salvar_saldo_nuvem(0.0)
        st.rerun()

# 5. JANELA MODAL (DIALOG)
@st.dialog("📝 **NOVO LANÇAMENTO**")
def cadastrar_dialog():
    tipo = st.selectbox("**Operação**", ["Receita", "Gasto"])
    cat = st.selectbox("**Categoria**", ["Trabalho", "Fixo", "Variável", "Lazer", "Saúde", "Investimento"])
    desc = st.text_input("**Descrição**")
    valor_in = st.number_input("**Valor R$**", min_value=0.0)
    data_in = st.date_input("**Data**", value=date.today())
    perc_inv = st.slider("**Investir (%)**", 0, 100, 0) if tipo == "Receita" else 0
    
    if st.button("**CONFIRMAR E SALVAR**", use_container_width=True):
        if valor_in > 0:
            nova = pd.DataFrame([[str(data_in), tipo, cat, desc, valor_in]], columns=cols_trans)
            salvar_dados(pd.concat([df_transacoes, nova], ignore_index=True), 'vendas')
            if tipo == "Receita" and perc_inv > 0:
                v_res = (valor_in * perc_inv) / 100
                salvar_saldo_nuvem(obter_saldo_nuvem() + v_res)
            st.rerun()

st.divider()
if st.button("📝 LANÇAR NOVA TRANSAÇÃO", key="btn_gravar", use_container_width=True, type="primary"):
    cadastrar_dialog()

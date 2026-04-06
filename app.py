import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURAÇÕES DE LAYOUT E CONEXÃO
st.set_page_config(page_title="Financeiro Pro", layout="wide", initial_sidebar_state="collapsed")

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1epf2H2ZjrmmXrS2OV-8W3P7LC7dp2FKJTHumWNevVeo/edit#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

# Limpeza de cache para garantir atualização dos gráficos
if 'limpeza_inicial' not in st.session_state:
    st.cache_data.clear()
    st.session_state.limpeza_inicial = True

# --- TEMA ---
modo_escuro = st.toggle("🌙 Modo Escuro")
COR_PRIMARIA = "#2d6a4f"
PLOT_THEME = "plotly_dark" if modo_escuro else "plotly_white"

st.markdown(f"""
    <style>
    h1 {{ background: linear-gradient(90deg, {COR_PRIMARIA}, #40916c); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900; text-align: center; }}
    .stTabs [data-baseweb="tab-list"] {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; }}
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

# Inicialização de Colunas
cols_trans = ['Data', 'Tipo', 'Categoria', 'Descricao', 'Valor']
cols_inv = ['Data', 'Tipo_Ativo', 'Descricao', 'Valor_Aplicado', 'Taxa_Anual', 'Meta_Destino']
cols_metas = ['Nome_Meta', 'Valor_Objetivo']

df_transacoes = carregar_dados('vendas', cols_trans)
df_invest = carregar_dados('investimentos', cols_inv)
df_metas = carregar_dados('metas', cols_metas)
saldo_reservado = obter_saldo_nuvem()

# 3. CÁLCULOS
rec = df_transacoes[df_transacoes['Tipo'] == 'Receita']['Valor'].sum()
gas = df_transacoes[df_transacoes['Tipo'] == 'Gasto']['Valor'].sum()
# O saldo abate o que já foi gasto e o que está reservado para investir
saldo_cc = rec - gas - saldo_reservado

if not df_invest.empty:
    total_inv = df_invest['Valor_Aplicado'].sum()
else: total_inv = 0.0

# 4. INTERFACE PRINCIPAL
st.markdown("<h1>💼 FINANCEIRO PRO</h1>", unsafe_allow_html=True)

c1, c2 = st.columns(2)
c1.metric("💰 Saldo Disponível (Conta)", f"R$ {saldo_cc:,.2f}")
c2.metric("📈 Total Investido", f"R$ {total_inv:,.2f}")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 DASH", "📈 CARTEIRA", "🎯 METAS", "📅 ANUAL", "⚙️ AJUSTES"])

with tab1:
    st.subheader("Análise de Gastos")
    df_g = df_transacoes[df_transacoes['Tipo'] == 'Gasto']
    if not df_g.empty:
        fig = px.pie(df_g, values='Valor', names='Categoria', hole=0.5, color_discrete_sequence=px.colors.sequential.Greens_r)
        fig.update_layout(template=PLOT_THEME, paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
    else: st.info("Sem gastos para exibir.")

with tab2:
    if saldo_reservado > 0:
        st.warning(f"🏦 Valor reservado para aporte: **R$ {saldo_reservado:,.2f}**")
        with st.expander("EFETUAR APORTE"):
            col_a, col_b = st.columns(2)
            t_at = col_a.selectbox("Ativo", ["CDB", "Ações", "FIIs", "Tesouro"])
            tx_at = col_b.number_input("Taxa Anual %", value=12.0)
            nm_at = st.text_input("Papel (Ex: MXRF11)")
            m_dest = st.selectbox("Destinar à Meta:", df_metas['Nome_Meta'].tolist() if not df_metas.empty else ["Geral"])
            
            if st.button("Confirmar Investimento"):
                novo = pd.DataFrame([[str(date.today()), t_at, nm_at, saldo_reservado, tx_at, m_dest]], columns=cols_inv)
                salvar_dados(pd.concat([df_invest, novo], ignore_index=True), 'investimentos')
                salvar_saldo_nuvem(0.0)
                st.rerun()
    st.subheader("Sua Carteira")
    st.dataframe(df_invest, use_container_width=True)

with tab3:
    st.subheader("Metas Financeiras")
    if not df_metas.empty:
        for _, m in df_metas.iterrows():
            progresso = df_invest[df_invest['Meta_Destino'] == m['Nome_Meta']]['Valor_Aplicado'].sum() if not df_invest.empty else 0
            st.write(f"**{m['Nome_Meta']}** (R$ {progresso:,.2f} de R$ {m['Valor_Objetivo']:,.2f})")
            st.progress(min(progresso / m['Valor_Objetivo'], 1.0))
    
    with st.expander("Adicionar Nova Meta"):
        n_m = st.text_input("Nome da Meta")
        v_m = st.number_input("Valor Alvo", min_value=1.0)
        if st.button("Salvar Meta"):
            salvar_dados(pd.concat([df_metas, pd.DataFrame([[n_m, v_m]], columns=cols_metas)], ignore_index=True), 'metas')
            st.rerun()

with tab4:
    st.subheader("Evolução Mensal")
    if not df_transacoes.empty:
        df_anual = df_transacoes.copy().dropna(subset=['Data'])
        df_anual['Mes'] = df_anual['Data'].dt.strftime('%b/%Y')
        df_m = df_anual.groupby(['Mes', 'Tipo'])['Valor'].sum().reset_index()
        fig_m = px.bar(df_m, x='Mes', y='Valor', color='Tipo', barmode='group', color_discrete_map={'Receita':'#2d6a4f', 'Gasto':'#bc4749'})
        fig_m.update_layout(template=PLOT_THEME, paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_m, use_container_width=True)

with tab5:
    st.subheader("Gerenciamento de Dados")
    with st.expander("Editar Transações"):
        ed_v = st.data_editor(df_transacoes, num_rows="dynamic", use_container_width=True)
        if st.button("Atualizar Planilha"):
            salvar_dados(ed_v, 'vendas')
            st.rerun()
            
    st.divider()
    confirma = st.checkbox("Desejo apagar todos os registros.")
    if st.button("LIMPAR TUDO", type="primary", disabled=not confirma):
        salvar_dados(pd.DataFrame(columns=cols_trans), 'vendas')
        salvar_dados(pd.DataFrame(columns=cols_inv), 'investimentos')
        salvar_saldo_nuvem(0.0)
        st.rerun()

# 5. DIÁLOGO DE LANÇAMENTO
@st.dialog("📝 NOVO LANÇAMENTO")
def cadastrar_dialog():
    tipo = st.selectbox("Operação", ["Receita", "Gasto"])
    cat = st.selectbox("Categoria", ["Trabalho", "Fixo", "Variável", "Lazer", "Saúde", "Investimento"])
    desc = st.text_input("Descrição")
    valor_in = st.number_input("Valor R$", min_value=0.0)
    data_in = st.date_input("Data", value=date.today())
    
    perc_inv = 0
    if tipo == "Receita":
        perc_inv = st.slider("Separar para Investimento (%)", 0, 100, 0)
    
    if st.button("SALVAR", use_container_width=True):
        if valor_in > 0:
            nova = pd.DataFrame([[str(data_in), tipo, cat, desc, valor_in]], columns=cols_trans)
            salvar_dados(pd.concat([df_transacoes, nova], ignore_index=True), 'vendas')
            
            if tipo == "Receita" and perc_inv > 0:
                v_res = (valor_in * perc_inv) / 100
                salvar_saldo_nuvem(obter_saldo_nuvem() + v_res)
            st.rerun()

st.divider()
if st.button("📝 LANÇAR NOVA TRANSAÇÃO", use_container_width=True, type="primary"):
    cadastrar_dialog()

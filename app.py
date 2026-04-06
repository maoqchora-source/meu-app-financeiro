import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURAÇÕES
st.set_page_config(page_title="Financeiro Pro", layout="wide", initial_sidebar_state="collapsed")

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1epf2H2ZjrmmXrS2OV-8W3P7LC7dp2FKJTHumWNevVeo/edit#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

if 'limpeza' not in st.session_state:
    st.cache_data.clear()
    st.session_state.limpeza = True

# --- TEMA E CORES ---
modo_escuro = st.toggle("🌙 Modo Escuro")
COR_RECEITA = "#2d6a4f" # Verde
COR_GASTO = "#bc4749"   # Vermelho
PLOT_THEME = "plotly_dark" if modo_escuro else "plotly_white"

st.markdown(f"""
    <style>
    h1 {{ background: linear-gradient(90deg, #2d6a4f, #40916c); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900; text-align: center; }}
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

# Inicialização
cols_trans = ['Data', 'Tipo', 'Categoria', 'Descricao', 'Valor']
cols_inv = ['Data', 'Tipo_Ativo', 'Descricao', 'Valor_Aplicado', 'Taxa_Anual', 'Meta_Destino']
cols_metas = ['Nome_Meta', 'Valor_Objetivo']

df_transacoes = carregar_dados('vendas', cols_trans)
df_invest = carregar_dados('investimentos', cols_inv)
df_metas = carregar_dados('metas', cols_metas)
saldo_reservado = obter_saldo_nuvem()

# 3. CÁLCULOS
total_rec = df_transacoes[df_transacoes['Tipo'] == 'Receita']['Valor'].sum()
total_gas = df_transacoes[df_transacoes['Tipo'] == 'Gasto']['Valor'].sum()
saldo_cc = total_rec - total_gas - saldo_reservado
total_inv = df_invest['Valor_Aplicado'].sum() if not df_invest.empty else 0.0

# 4. INTERFACE
st.markdown("<h1>💼 FINANCEIRO PRO</h1>", unsafe_allow_html=True)

c1, c2 = st.columns(2)
c1.metric("💰 Saldo em Conta (Livre)", f"R$ {saldo_cc:,.2f}")
c2.metric("📈 Total Investido", f"R$ {total_inv:,.2f}")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 DASH", "📈 CARTEIRA", "🎯 METAS", "📅 ANUAL", "⚙️ AJUSTES"])

with tab1:
    st.subheader("Para onde vai seu dinheiro? (Gastos)")
    df_g = df_transacoes[df_transacoes['Tipo'] == 'Gasto']
    if not df_g.empty:
        # Gráfico de Pizza focado em categorias de Gasto
        fig_pizza = px.pie(df_g, values='Valor', names='Categoria', hole=0.5, 
                           color_discrete_sequence=px.colors.sequential.Reds_r)
        fig_pizza.update_layout(template=PLOT_THEME, paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_pizza, use_container_width=True)
    else: st.info("Lance alguns gastos para ver o gráfico.")

with tab2:
    if saldo_reservado > 0:
        st.warning(f"🏦 Saldo para Aporte: **R$ {saldo_reservado:,.2f}**")
        if st.button("Confirmar Aplicação de Reserva"):
            novo = pd.DataFrame([[str(date.today()), "Aporte", "Reserva", saldo_reservado, 12.0, "Geral"]], columns=cols_inv)
            salvar_dados(pd.concat([df_invest, novo], ignore_index=True), 'investimentos')
            salvar_saldo_nuvem(0.0)
            st.rerun()
    st.dataframe(df_invest, use_container_width=True)

with tab3:
    st.subheader("Suas Metas")
    if not df_metas.empty:
        for _, m in df_metas.iterrows():
            acumulado = df_invest[df_invest['Meta_Destino'] == m['Nome_Meta']]['Valor_Aplicado'].sum() if not df_invest.empty else 0
            st.write(f"**{m['Nome_Meta']}**")
            st.progress(min(acumulado / m['Valor_Objetivo'], 1.0))
    with st.expander("Nova Meta"):
        nm = st.text_input("Meta")
        vm = st.number_input("Valor", min_value=1.0)
        if st.button("Criar"):
            salvar_dados(pd.concat([df_metas, pd.DataFrame([[nm, vm]], columns=cols_metas)], ignore_index=True), 'metas')
            st.rerun()

with tab4:
    st.subheader("Fluxo de Caixa Mensal")
    if not df_transacoes.empty:
        df_anual = df_transacoes.copy().dropna(subset=['Data'])
        df_anual['Mes'] = df_anual['Data'].dt.strftime('%m/%Y') # Ordenação por número do mês
        df_m = df_anual.groupby(['Mes', 'Tipo'])['Valor'].sum().reset_index()
        
        fig_barra = px.bar(df_m, x='Mes', y='Valor', color='Tipo', barmode='group',
                           color_discrete_map={'Receita': COR_RECEITA, 'Gasto': COR_GASTO})
        fig_barra.update_layout(template=PLOT_THEME, paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_barra, use_container_width=True)

with tab5:
    st.subheader("⚙️ Configurações")
    ed_v = st.data_editor(df_transacoes, num_rows="dynamic", use_container_width=True)
    if st.button("Salvar Edições"):
        salvar_dados(ed_v, 'vendas')
        st.rerun()
    
    st.divider()
    if st.button("LIMPAR TUDO", type="primary"):
        salvar_dados(pd.DataFrame(columns=cols_trans), 'vendas')
        salvar_dados(pd.DataFrame(columns=cols_inv), 'investimentos')
        salvar_saldo_nuvem(0.0)
        st.rerun()

# 5. LANÇAMENTO
@st.dialog("📝 NOVO LANÇAMENTO")
def cadastrar_dialog():
    tipo = st.selectbox("Tipo", ["Receita", "Gasto"])
    cat = st.selectbox("Categoria", ["Trabalho", "Fixo", "Variável", "Lazer", "Saúde", "Investimento"])
    desc = st.text_input("Descrição")
    valor_in = st.number_input("Valor R$", min_value=0.0)
    data_in = st.date_input("Data", value=date.today())
    perc_inv = st.slider("Investir (%)", 0, 100, 0) if tipo == "Receita" else 0
    
    if st.button("SALVAR"):
        if valor_in > 0:
            nova = pd.DataFrame([[str(data_in), tipo, cat, desc, valor_in]], columns=cols_trans)
            salvar_dados(pd.concat([df_transacoes, nova], ignore_index=True), 'vendas')
            if tipo == "Receita" and perc_inv > 0:
                salvar_saldo_nuvem(obter_saldo_nuvem() + (valor_in * perc_inv / 100))
            st.rerun()

st.divider()
if st.button("📝 LANÇAR NOVA TRANSAÇÃO", use_container_width=True, type="primary"):
    cadastrar_dialog()

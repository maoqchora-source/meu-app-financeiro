import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import date, datetime

# 1. CONFIGURAÇÕES DE LAYOUT
st.set_page_config(page_title="Planejamento Financeiro", layout="wide", initial_sidebar_state="collapsed")

# Cores Corporativas
COR_PRIMARIA = '#2d6a4f'
COR_FUNDO = '#f8f9fa'
COR_TEXTO = '#2c3e50'

st.markdown(f"""
    <style>
    .stApp {{ background-color: {COR_FUNDO}; }}
    [data-testid="stMetricValue"] {{ color: {COR_PRIMARIA}; font-size: 2.5rem !important; text-align: center; }}
    [data-testid="stMetricLabel"] {{ text-align: center; }}
    
    /* Grid de Abas Arredondadas */
    .stTabs [data-baseweb="tab-list"] {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 10px;
    }}
    .stTabs [data-baseweb="tab"] {{
        background-color: white;
        border-radius: 15px;
        padding: 15px;
        box-shadow: 0px 2px 5px rgba(0,0,0,0.05);
        border: 1px solid #eee;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {COR_PRIMARIA} !important;
        color: white !important;
    }}

    /* Estilo do Botão Flutuante */
    div[data-testid="stVerticalBlock"] > div:has(button[key="fab"]) {{
        position: fixed;
        bottom: 30px;
        right: 30px;
        z-index: 999;
    }}
    .stButton>button[key="fab"] {{
        width: 60px !important;
        height: 60px !important;
        border-radius: 50% !important;
        background-color: {COR_PRIMARIA} !important;
        color: white !important;
        font-size: 30px !important;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.3) !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# 2. FUNÇÕES DE DADOS
def carregar_dados(arquivo, colunas):
    if os.path.exists(arquivo):
        try:
            df = pd.read_csv(arquivo)
            if not df.empty and 'Data' in df.columns:
                df['Data'] = pd.to_datetime(df['Data']).dt.date
            return df.reindex(columns=colunas)
        except: return pd.DataFrame(columns=colunas)
    return pd.DataFrame(columns=colunas)

def salvar_dados(df, arquivo):
    df.to_csv(arquivo, index=False)

cols_trans = ['Data', 'Tipo', 'Categoria', 'Descricao', 'Valor']
cols_inv = ['Data', 'Tipo_Ativo', 'Descricao', 'Valor_Aplicado', 'Taxa_Anual', 'Meta_Destino']
cols_metas = ['Nome_Meta', 'Valor_Objetivo']

df_transacoes = carregar_dados('banco_cc.csv', cols_trans)
df_invest = carregar_dados('investimentos.csv', cols_inv)
df_metas = carregar_dados('metas.csv', cols_metas)

if not os.path.exists('saldo_aporte.txt'):
    with open('saldo_aporte.txt', 'w') as f: f.write('0.0')
with open('saldo_aporte.txt', 'r') as f:
    st.session_state.saldo_para_aportar = float(f.read())

def atualizar_saldo_aporte(valor):
    st.session_state.saldo_para_aportar = valor
    with open('saldo_aporte.txt', 'w') as f: f.write(str(valor))

# 3. JANELA MODAL (DIALOG)
@st.dialog("📝 Novo Lançamento")
def cadastrar_dialog():
    tipo = st.selectbox("Operação", ["Receita", "Gasto"])
    cat = st.selectbox("Categoria", ["Trabalho", "Fixo", "Variável", "Lazer", "Saúde", "Investimento"])
    desc = st.text_input("Descrição")
    valor_in = st.number_input("Valor R$", min_value=0.0)
    data_in = st.date_input("Data")
    perc_inv = 0
    if tipo == "Receita":
        perc_inv = st.slider("Investir (%)", 0, 100, 0)
    
    if st.button("Gravar Dados"):
        if valor_in > 0:
            global df_transacoes
            nova = pd.DataFrame([[data_in, tipo, cat, desc, valor_in]], columns=cols_trans)
            df_transacoes = pd.concat([df_transacoes, nova], ignore_index=True)
            
            if tipo == "Receita" and perc_inv > 0:
                v_inv = (valor_in * perc_inv) / 100
                ajuste = pd.DataFrame([[data_in, "Gasto", "Investimento", f"Reserva: {desc}", v_inv]], columns=cols_trans)
                df_transacoes = pd.concat([df_transacoes, ajuste], ignore_index=True)
                atualizar_saldo_aporte(st.session_state.saldo_para_aportar + v_inv)
            
            salvar_dados(df_transacoes, 'banco_cc.csv')
            st.success("Salvo!")
            st.rerun()

# 4. PROCESSAMENTO E MÉTRICAS
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

# EXIBIÇÃO
st.markdown("<h2 style='text-align: center;'>💼 Planejamento Financeiro</h2>", unsafe_allow_html=True)
st.metric("Disponível em Conta", f"R$ {saldo_cc:,.2f}")
st.metric("Patrimônio Investido", f"R$ {total_inv:,.2f}")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dash", "📈 Carteira", "🎯 Metas", "📅 Anual", "⚙️ Ajustes"])

with tab1:
    if not df_transacoes.empty:
        df_g = df_transacoes[(df_transacoes['Tipo']=='Gasto') & (df_transacoes['Categoria']!='Investimento')]
        if not df_g.empty:
            fig = px.pie(df_g, values='Valor', names='Categoria', hole=0.5, color_discrete_sequence=['#2d6a4f', '#74c69d', '#adb5bd'])
            st.plotly_chart(fig, use_container_width=True)
    else: st.info("Sem dados.")

with tab2:
    if st.session_state.saldo_para_aportar > 0:
        st.warning(f"Reserva p/ Aplicar: R$ {st.session_state.saldo_para_aportar:,.2f}")
        if st.button("Aplicar Reserva"):
            # Aqui você pode adicionar lógica rápida ou apenas informar para usar o Ajustes
            pass
    st.dataframe(df_invest, use_container_width=True)

with tab3:
    if not df_metas.empty:
        for i, m in df_metas.iterrows():
            acum = df_invest[df_invest['Meta_Destino']==m['Nome_Meta']]['Valor_Atualizado'].sum() if not df_invest.empty else 0
            st.write(f"**{m['Nome_Meta']}**")
            st.progress(min(acum/m['Valor_Objetivo'], 1.0))

with tab5:
    st.subheader("Configurações")
    if st.button("Limpar Todos os Dados"):
        for a in ['banco_cc.csv', 'investimentos.csv', 'metas.csv', 'saldo_aporte.txt']:
            if os.path.exists(a): os.remove(a)
        st.rerun()

# BOTÃO FLUTUANTE (FAB)
if st.button("+", key="fab"):
    cadastrar_dialog()

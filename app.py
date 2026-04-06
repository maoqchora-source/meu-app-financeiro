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
    
    /* Negrito nas métricas e títulos */
    [data-testid="stMetricValue"] {{ 
        color: {COR_PRIMARIA}; 
        font-size: 2.5rem !important; 
        text-align: center; 
        font-weight: 800 !important; 
    }}
    [data-testid="stMetricLabel"] {{ 
        text-align: center; 
        font-weight: bold !important; 
        color: {COR_TEXTO}; 
        font-size: 1.1rem !important;
    }}
    
    /* Grid de Abas Arredondadas com Negrito */
    .stTabs [data-baseweb="tab-list"] {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 10px;
        margin-bottom: 20px;
    }}
    .stTabs [data-baseweb="tab"] {{
        background-color: white;
        border-radius: 15px;
        padding: 15px;
        box-shadow: 0px 2px 5px rgba(0,0,0,0.05);
        border: 1px solid #eee;
        height: 80px;
        font-weight: bold !important;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {COR_PRIMARIA} !important;
        color: white !important;
    }}

    /* Botão GRAVAR DADOS Estilizado */
    div[data-testid="stVerticalBlock"] > div:has(button[key="btn_gravar"]) {{
        position: fixed;
        bottom: 20px;
        left: 5%;
        right: 5%;
        z-index: 999;
    }}
    .stButton>button[key="btn_gravar"] {{
        width: 90vw !important;
        height: 60px !important;
        border-radius: 15px !important;
        background-color: {COR_PRIMARIA} !important;
        color: white !important;
        font-size: 20px !important;
        font-weight: 900 !important;
        box-shadow: 0px 6px 20px rgba(0,0,0,0.3) !important;
        border: none !important;
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
            df_transacoes = pd.concat([df_transacoes, nova], ignore_index=True)
            
            if tipo == "Receita" and perc_inv > 0:
                v_inv = (valor_in * perc_inv) / 100
                ajuste = pd.DataFrame([[data_in, "Gasto", "Investimento", f"Reserva: {desc}", v_inv]], columns=cols_trans)
                df_transacoes = pd.concat([df_transacoes, ajuste], ignore_index=True)
                atualizar_saldo_aporte(st.session_state.saldo_para_aportar + v_inv)
            
            salvar_dados(df_transacoes, 'banco_cc.csv')
            st.success("**DADOS GRAVADOS COM SUCESSO!**")
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
st.markdown("<h1 style='text-align: center;'>💼 **PLANEJAMENTO FINANCEIRO**</h1>", unsafe_allow_html=True)
st.metric("**DISPONÍVEL EM CONTA**", f"R$ {saldo_cc:,.2f}")
st.metric("**PATRIMÔNIO INVESTIDO**", f"R$ {total_inv:,.2f}")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["**📊 DASH**", "**📈 CARTEIRA**", "**🎯 METAS**", "**📅 ANUAL**", "**⚙️ AJUSTES**"])

with tab1:
    st.markdown("### **DISTRIBUIÇÃO DE GASTOS**")
    if not df_transacoes.empty:
        df_g = df_transacoes[(df_transacoes['Tipo']=='Gasto') & (df_transacoes['Categoria']!='Investimento')]
        if not df_g.empty:
            fig = px.pie(df_g, values='Valor', names='Categoria', hole=0.5, color_discrete_sequence=['#2d6a4f', '#40916c', '#74c69d', '#95d5b2'])
            st.plotly_chart(fig, use_container_width=True)
    else: st.info("**NENHUM DADO REGISTRADO AINDA.**")

with tab2:
    st.subheader("🏦 Carteira de Ativos")
    if st.session_state.saldo_para_aportar > 0:
        st.info(f"💰 Você tem **R$ {st.session_state.saldo_para_aportar:,.2f}** reservados para aplicar.")
        col_a, col_b = st.columns(2)
        t_at = col_a.selectbox("Tipo:", ["CDI", "LCA", "FIIs", "Ações"])
        tx_at = col_b.number_input("Taxa Anual %", value=12.0)
        nm_at = st.text_input("Nome do Papel (Ex: CDB Banco X)")
        m_dest = st.selectbox("Destinar p/ Meta:", df_metas['Nome_Meta'].tolist() if not df_metas.empty else ["Geral"])
        
        if st.button("Confirmar Aplicação"):
            novo = pd.DataFrame([[date.today(), t_at, nm_at, st.session_state.saldo_para_aportar, tx_at, m_dest]], columns=cols_inv)
            df_invest = pd.concat([df_invest, novo], ignore_index=True)
            salvar_dados(df_invest, 'investimentos.csv')
            atualizar_saldo_aporte(0.0)
            st.success("Investimento registrado!")
            st.rerun()
    
    if not df_invest.empty:
        st.dataframe(df_invest[['Tipo_Ativo', 'Descricao', 'Valor_Atualizado', 'Meta_Destino']], use_container_width=True)

with tab3:
    st.subheader("🚩 Objetivos")
    with st.expander("➕ Nova Meta"):
        n_meta = st.text_input("Nome da Meta")
        v_meta = st.number_input("Valor Alvo", min_value=1.0)
        if st.button("Criar Meta"):
            if n_meta:
                nova_m = pd.DataFrame([[n_meta, v_meta]], columns=cols_metas)
                df_metas = pd.concat([df_metas, nova_m], ignore_index=True)
                salvar_dados(df_metas, 'metas.csv')
                st.rerun()

    if not df_metas.empty:
        for i, m in df_metas.iterrows():
            acumulado = df_invest[df_invest['Meta_Destino'] == m['Nome_Meta']]['Valor_Atualizado'].sum() if not df_invest.empty else 0
            progresso = min(acumulado / m['Valor_Objetivo'], 1.0)
            st.write(f"**{m['Nome_Meta']}**")
            st.progress(progresso)
            st.caption(f"R$ {acumulado:,.2f} de R$ {m['Valor_Objetivo']:,.2f}")

with tab4:
    if not df_transacoes.empty:
        df_transacoes['Data'] = pd.to_datetime(df_transacoes['Data'])
        df_transacoes['Mes'] = df_transacoes['Data'].dt.strftime('%b/%Y')
        df_mensal = df_transacoes.groupby(['Mes', 'Tipo'])['Valor'].sum().reset_index()
        fig_anual = px.bar(df_mensal, x='Mes', y='Valor', color='Tipo', barmode='group', 
                          color_discrete_map={'Receita':COR_PRIMARIA, 'Gasto':'#adb5bd'})
        st.plotly_chart(fig_anual, use_container_width=True)
with tab5:
    st.subheader("**ADMINISTRAÇÃO DO APP**")
    with st.expander("**✏️ EDITAR TRANSAÇÕES (BANCO CC)**"):
        df_e = st.data_editor(df_transacoes, num_rows="dynamic", use_container_width=True)
        if st.button("**SALVAR ALTERAÇÕES**"):
            salvar_dados(df_e, 'banco_cc.csv')
            st.rerun()
    
    st.divider()
    if st.button("**🚨 ZERAR TODOS OS DADOS**"):
        for a in ['banco_cc.csv', 'investimentos.csv', 'metas.csv', 'saldo_aporte.txt']:
            if os.path.exists(a): os.remove(a)
        st.rerun()

# 6. BOTÃO PRINCIPAL "GRAVAR DADOS"
if st.button("GRAVAR DADOS", key="btn_gravar"):
    cadastrar_dialog()

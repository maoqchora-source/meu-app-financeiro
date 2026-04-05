import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import date, datetime

# 1. CONFIGURAÇÕES DE LAYOUT E CORES
st.set_page_config(page_title="Planejamento Financeiro", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    h1, h2, h3 { color: #2c3e50 !important; font-family: 'Segoe UI', sans-serif; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; background-color: #ffffff; padding: 10px; border-radius: 10px; box-shadow: 0px 2px 5px rgba(0,0,0,0.05); }
    .stTabs [aria-selected="true"] { background-color: #2d6a4f !important; color: white !important; }
    [data-testid="stMetricValue"] { color: #2d6a4f; }
    .stButton>button { background-color: #2d6a4f; color: white; border-radius: 8px; width: 100%; }
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

# Carregar saldo de aporte persistente
if not os.path.exists('saldo_aporte.txt'):
    with open('saldo_aporte.txt', 'w') as f: f.write('0.0')

with open('saldo_aporte.txt', 'r') as f:
    st.session_state.saldo_para_aportar = float(f.read())

def atualizar_saldo_aporte(valor):
    st.session_state.saldo_para_aportar = valor
    with open('saldo_aporte.txt', 'w') as f: f.write(str(valor))

def calcular_valor_atual(row):
    try:
        data_inv = row['Data']
        if isinstance(data_inv, str): data_inv = datetime.strptime(data_inv, '%Y-%m-%d').date()
        dias = (date.today() - data_inv).days
        if dias <= 0: return row['Valor_Aplicado']
        taxa_diaria = (1 + (row['Taxa_Anual']/100))**(1/365) - 1
        return row['Valor_Aplicado'] * (1 + taxa_diaria)**dias
    except: return row['Valor_Aplicado']

# 3. SIDEBAR (LOGICA CORRIGIDA)
with st.sidebar:
    st.markdown("### 🏦 Novo Lançamento")
    tipo = st.selectbox("Operação", ["Receita", "Gasto"])
    cat = st.selectbox("Categoria", ["Trabalho", "Fixo", "Variável", "Lazer", "Saúde", "Investimento"])
    desc = st.text_input("Descrição")
    valor_input = st.number_input("Valor R$", min_value=0.0)
    data_in = st.date_input("Data")
    
    perc_inv = 0
    if tipo == "Receita":
        perc_inv = st.slider("Destinar p/ Investimento (%)", 0, 100, 0)
    
    if st.button("🚀 GRAVAR"):
        if valor_input > 0:
            # 1. Registra a transação principal
            nova_trans = pd.DataFrame([[data_in, tipo, cat, desc, valor_input]], columns=cols_trans)
            df_transacoes = pd.concat([df_transacoes, nova_trans], ignore_index=True)
            
            # 2. Se for Receita com % de investimento, desconta do saldo
            if tipo == "Receita" and perc_inv > 0:
                valor_investir = (valor_input * perc_inv) / 100
                # Registra um "Gasto" de categoria Investimento para abater do saldo em conta
                trans_ajuste = pd.DataFrame([[data_in, "Gasto", "Investimento", f"Reserva p/ Investir ({desc})", valor_investir]], columns=cols_trans)
                df_transacoes = pd.concat([df_transacoes, trans_ajuste], ignore_index=True)
                
                # Aumenta o saldo que fica disponível na aba Carteira
                atualizar_saldo_aporte(st.session_state.saldo_para_aportar + valor_investir)
            
            salvar_dados(df_transacoes, 'banco_cc.csv')
            st.success("Lançado com sucesso!")
            st.rerun()

# 4. PROCESSAMENTO
if not df_invest.empty:
    df_invest['Valor_Atualizado'] = df_invest.apply(calcular_valor_atual, axis=1)
    total_inv = df_invest['Valor_Atualizado'].sum()
else: total_inv = 0

# O saldo em conta agora considera os "Gastos" de investimento como saídas
rec = df_transacoes[df_transacoes['Tipo'] == 'Receita']['Valor'].sum()
gas = df_transacoes[df_transacoes['Tipo'] == 'Gasto']['Valor'].sum()
saldo_cc = rec - gas

# 5. LAYOUT
st.title("💼 Planejamento Financeiro")
c1, c2 = st.columns(2)
c1.metric("Disponível em Conta", f"R$ {saldo_cc:,.2f}")
c2.metric("Patrimônio Investido", f"R$ {total_inv:,.2f}")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 DASHBOARD", "📈 CARTEIRA", "🎯 METAS", "📅 ANUAL", "⚙️ AJUSTES"])

paleta_corp = ['#2d6a4f', '#40916c', '#52b788', '#74c69d', '#95d5b2', '#adb5bd', '#6c757d', '#495057']

with tab1:
    if not df_transacoes.empty:
        df_gasto = df_transacoes[(df_transacoes['Tipo']=='Gasto') & (df_transacoes['Categoria'] != 'Investimento')]
        if not df_gasto.empty:
            fig = px.pie(df_gasto, values='Valor', names='Categoria', hole=0.5, color_discrete_sequence=paleta_corp, title="Gastos Reais (Excluindo Reservas)")
            st.plotly_chart(fig, use_container_width=True)
        st.write("**Resumo de Fluxo:**")
        st.write(f"Receitas: R$ {rec:,.2f} | Saídas/Reservas: R$ {gas:,.2f}")

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
                          color_discrete_map={'Receita':'#2d6a4f', 'Gasto':'#adb5bd'})
        st.plotly_chart(fig_anual, use_container_width=True)

with tab5:
    st.subheader("⚙️ Ajustes")
    with st.expander("✏️ Editar Lançamentos (Banco CC)"):
        df_trans_editada = st.data_editor(df_transacoes, num_rows="dynamic", use_container_width=True)
        if st.button("Salvar Edições Banco"):
            salvar_dados(df_trans_editada, 'banco_cc.csv')
            st.rerun()

    with st.expander("✏️ Editar Ativos"):
        df_inv_editada = st.data_editor(df_invest, num_rows="dynamic", use_container_width=True)
        if st.button("Salvar Edições Ativos"):
            salvar_dados(df_inv_editada, 'investimentos.csv')
            st.rerun()

    st.divider()
    if st.button("🚨 ZERAR TUDO"):
        for arq in ['banco_cc.csv', 'investimentos.csv', 'metas.csv', 'saldo_aporte.txt']:
            if os.path.exists(arq): os.remove(arq)
        atualizar_saldo_aporte(0.0)
        st.rerun()

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import date, datetime

# 1. CONFIGURAÇÕES DE LAYOUT
st.set_page_config(page_title="Planejamento Financeiro", layout="wide", initial_sidebar_state="collapsed")

# Cores Corporativas
COR_PRIMARIA = '#2d6a4f'
COR_FUNDO = '#f8f9fa'
COR_TEXTO = '#2c3e50'

# Estilos customizados
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700;900&display=swap');
    html, body, [class*="css"] {{
        font-family: 'Montserrat', sans-serif;
    }}
    .stApp {{ background-color: {COR_FUNDO}; }}

    h1 {{
      background: linear-gradient(90deg, #2d6a4f, #40916c);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      font-weight: 900;
      text-align: center;
    }}

    .card {{
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.1);
        text-align: center;
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
        except:
            return pd.DataFrame(columns=colunas)
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
    
    if st.button("💾 CONFIRMAR E SALVAR"):
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
            st.toast("✅ Dados gravados com sucesso!")
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
    st.markdown(f"<div class='card'><h3>💰 Disponível em Conta</h3><h2>R$ {saldo_cc:,.2f}</h2></div>", unsafe_allow_html=True)
with col2:
    st.markdown(f"<div class='card'><h3>📈 Patrimônio Investido</h3><h2>R$ {total_inv:,.2f}</h2></div>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["**📊 DASH**", "**📈 CARTEIRA**", "**🎯 METAS**", "**📅 ANUAL**", "**⚙️ AJUSTES**"])

with tab1:
    st.markdown("### **DISTRIBUIÇÃO DE GASTOS**")
    if not df_transacoes.empty:
        df_g = df_transacoes[(df_transacoes['Tipo']=='Gasto') & (df_transacoes['Categoria']!='Investimento')]
        if not df_g.empty:
            fig = px.pie(df_g, values='Valor', names='Categoria', hole=0.5,
                         color_discrete_sequence=['#2d6a4f', '#40916c', '#74c69d', '#95d5b2'])
            st.plotly_chart(fig, use_container_width=True)
    else: st.info("**NENHUM DADO REGISTRADO AINDA.**")

with tab2:
    st.subheader("**CARTEIRA DE ATIVOS**")
    if st.session_state.saldo_para_aportar > 0:
        st.warning(f"**💰 SALDO PARA APLICAR: R$ {st.session_state.saldo_para_aportar:,.2f}**")
    st.dataframe(df_invest, use_container_width=True)

with tab3:
    st.subheader("**PROGRESSO DAS METAS**")
    if not df_metas.empty:
        for i, m in df_metas.iterrows():
            acum = df_invest[df_invest['Meta_Destino']==m['Nome_Meta']]['Valor_Atualizado'].sum() if not df_invest.empty else 0
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=acum,
                title={'text': m['Nome_Meta']},
                gauge={'axis': {'range': [None, m['Valor_Objetivo']]},
                       'bar': {'color': COR_PRIMARIA}}
            ))
            st.plotly_chart(fig, use_container_width=True)

with tab5:
    st.subheader("**ADMINISTRAÇÃO DO APP**")
    with st.expander("**✏️ EDITAR TRANSAÇÕES (BANCO CC)**"):
        df_e = st.data_editor(df_transacoes, num_rows="dynamic", use_container_width=True)
        if st.button("💾 SALVAR ALTERAÇÕES"):
            salvar_dados(df_e, 'banco_cc.csv')
            st.toast("✅ Alterações salvas!")
            st.rerun()
    
    st.divider()
    if st.button("🚨 ZERAR TODOS OS DADOS"):
        for a in ['banco_cc.csv', 'investimentos.csv', 'metas.csv', 'saldo_aporte.txt']:
            if os.path.exists(a): 


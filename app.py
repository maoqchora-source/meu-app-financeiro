import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURAÇÕES
st.set_page_config(page_title="Financeiro Pro", layout="wide", initial_sidebar_state="collapsed")

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1epf2H2ZjrmmXrS2OV-8W3P7LC7dp2FKJTHumWNevVeo/edit#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CORES ---
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

st.markdown(f"""
    <style>
    .stApp {{ background: {GRADIENTE}; }}
    h1 {{ background: linear-gradient(90deg, {COR_PRIMARIA}, #40916c); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900; text-align: center; }}
    .card {{ background-color: {CARD_BG}; color: {CARD_TEXT}; padding: 20px; border-radius: 15px; box-shadow: 0px 4px 15px rgba(0,0,0,0.1); text-align: center; margin-bottom: 15px; }}
    .stTabs [data-baseweb="tab-list"] {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; }}
    </style>
""", unsafe_allow_html=True)

# 2. FUNÇÕES DE DADOS
def carregar_dados(aba, colunas):
    try:
        df = conn.read(spreadsheet=URL_PLANILHA, worksheet=aba, ttl="0")
        if df is None or df.empty:
            return pd.DataFrame(columns=colunas)
        return df
    except:
        return pd.DataFrame(columns=colunas)

def salvar_dados(df, aba):
    conn.update(spreadsheet=URL_PLANILHA, worksheet=aba, data=df)
    st.cache_data.clear()

def obter_saldo_nuvem():
    try:
        df_conf = conn.read(spreadsheet=URL_PLANILHA, worksheet='config', ttl="0")
        return float(df_conf.iloc[0, 0])
    except:
        return 0.0

def salvar_saldo_nuvem(valor):
    df_conf = pd.DataFrame([[valor]], columns=['saldo_aporte'])
    conn.update(spreadsheet=URL_PLANILHA, worksheet='config', data=df_conf)
    st.cache_data.clear()

# Inicialização
cols_trans = ['Data', 'Tipo', 'Categoria', 'Descricao', 'Valor']
cols_inv = ['Data', 'Tipo_Ativo', 'Descricao', 'Valor_Aplicado', 'Taxa_Anual', 'Meta_Destino']
cols_metas = ['Nome_Meta', 'Valor_Objetivo']

df_transacoes = carregar_dados('vendas', cols_trans)
df_invest = carregar_dados('investimentos', cols_inv)
df_metas = carregar_dados('metas', cols_metas)

# 3. JANELA DE LANÇAMENTO
@st.dialog("📝 NOVO LANÇAMENTO")
def cadastrar_dialog():
    tipo = st.selectbox("Tipo", ["Receita", "Gasto"])
    cat = st.selectbox("Categoria", ["Trabalho", "Fixo", "Variável", "Lazer", "Saúde", "Investimento"])
    desc = st.text_input("Descrição")
    valor_in = st.number_input("Valor R$", min_value=0.0, step=10.0)
    data_in = st.date_input("Data", value=date.today())
    
    perc_inv = 0
    if tipo == "Receita":
        perc_inv = st.slider("Reservar para Investir (%)", 0, 100, 0)
    
    if st.button("SALVAR AGORA", use_container_width=True):
        if valor_in > 0:
            # Salvar na aba vendas
            nova_linha = pd.DataFrame([[str(data_in), tipo, cat, desc, valor_in]], columns=cols_trans)
            df_novo = pd.concat([df_transacoes, nova_linha], ignore_index=True)
            salvar_dados(df_novo, 'vendas')
            
            # Lógica de Saldo para Aporte
            if tipo == "Receita" and perc_inv > 0:
                v_reserva = (valor_in * perc_inv) / 100
                novo_total_reserva = obter_saldo_nuvem() + v_reserva
                salvar_saldo_nuvem(novo_total_reserva)
            
            st.success("Lançamento concluído!")
            st.rerun()

# 4. CÁLCULOS
total_receitas = df_transacoes[df_transacoes['Tipo'] == 'Receita']['Valor'].sum()
total_gastos = df_transacoes[df_transacoes['Tipo'] == 'Gasto']['Valor'].sum()
saldo_atual = total_receitas - total_gastos

# Cálculo de Investimentos com Juros Simples/Compostos Diários para exibição
if not df_invest.empty:
    df_invest['Valor_Atual'] = df_invest.apply(lambda x: x['Valor_Aplicado'] * (1 + (x['Taxa_Anual']/100)/365)**(date.today() - pd.to_datetime(x['Data']).date()).days, axis=1)
    total_investido = df_invest['Valor_Atual'].sum()
else:
    total_investido = 0.0

# 5. INTERFACE PRINCIPAL
st.markdown("<h1>💼 MEU FINANCEIRO</h1>", unsafe_allow_html=True)

c1, c2 = st.columns(2)
c1.markdown(f"<div class='card'><h5>💰 Saldo em Conta</h5><h2>R$ {saldo_atual:,.2f}</h2></div>", unsafe_allow_html=True)
c2.markdown(f"<div class='card'><h5>📈 Total Investido</h5><h2>R$ {total_investido:,.2f}</h2></div>", unsafe_allow_html=True)

t1, t2, t3, t4, t5 = st.tabs(["📊 DASHBOARD", "🚀 CARTEIRA", "🎯 METAS", "🗓️ HISTÓRICO", "⚙️ ADM"])

with t1:
    if not df_transacoes.empty:
        df_pizza = df_transacoes[df_transacoes['Tipo'] == 'Gasto']
        if not df_pizza.empty:
            fig = px.pie(df_pizza, values='Valor', names='Categoria', hole=0.4, title="Distribuição de Gastos", color_discrete_sequence=px.colors.sequential.Greens_r)
            fig.update_layout(template=PLOT_THEME, paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Lance gastos para ver o gráfico.")
    else:
        st.info("Nenhum dado encontrado.")

with t2:
    st.subheader("Investimentos")
    saldo_reserva = obter_saldo_nuvem()
    if saldo_reserva > 0:
        st.info(f"Você tem **R$ {saldo_reserva:,.2f}** reservados para aplicar.")
        with st.expander("EFETUAR APORTE AGORA"):
            tipo_at = st.selectbox("Ativo", ["CDB", "Ações", "FIIs", "Tesouro"])
            nome_at = st.text_input("Nome/Ticket (ex: MXRF11)")
            taxa_at = st.number_input("Taxa Anual (%)", value=12.0)
            meta_at = st.selectbox("Vincular à Meta", df_metas['Nome_Meta'].tolist() if not df_metas.empty else ["Geral"])
            
            if st.button("Confirmar Investimento"):
                novo_inv = pd.DataFrame([[str(date.today()), tipo_at, nome_at, saldo_reserva, taxa_at, meta_at]], columns=cols_inv)
                salvar_dados(pd.concat([df_invest, novo_inv], ignore_index=True), 'investimentos')
                salvar_saldo_nuvem(0.0) # AQUI ELE ZERA O SALDO
                st.success("Aporte realizado!")
                st.rerun()
    st.dataframe(df_invest, use_container_width=True)

with t3:
    st.subheader("Minhas Metas")
    if not df_metas.empty:
        for _, m in df_metas.iterrows():
            progresso = df_invest[df_invest['Meta_Destino'] == m['Nome_Meta']]['Valor_Aplicado'].sum() if not df_invest.empty else 0
            porcentagem = min(progresso / m['Valor_Objetivo'], 1.0)
            st.write(f"**{m['Nome_Meta']}**: R$ {progresso:,.2f} de R$ {m['Valor_Objetivo']:,.2f}")
            st.progress(porcentagem)
    
    with st.expander("Nova Meta"):
        n_m = st.text_input("Nome da Meta")
        v_m = st.number_input("Valor Objetivo", min_value=100.0)
        if st.button("Criar Meta"):
            salvar_dados(pd.concat([df_metas, pd.DataFrame([[n_m, v_m]], columns=cols_metas)], ignore_index=True), 'metas')
            st.rerun()

with t5:
    st.subheader("Gerenciar Dados")
    # Editor direto
    ed_v = st.data_editor(df_transacoes, num_rows="dynamic", use_container_width=True, key="v")
    if st.button("Salvar Alterações"):
        salvar_dados(ed_v, 'vendas')
        st.rerun()
    
    st.divider()
    if st.checkbox("LIBERAR LIMPEZA TOTAL"):
        if st.button("APAGAR TUDO", type="primary"):
            salvar_dados(pd.DataFrame(columns=cols_trans), 'vendas')
            salvar_dados(pd.DataFrame(columns=cols_inv), 'investimentos')
            salvar_saldo_nuvem(0.0)
            st.rerun()

# 6. BOTÃO FLUTUANTE
st.divider()
if st.button("➕ LANÇAR MOVIMENTAÇÃO", use_container_width=True, type="primary"):
    cadastrar_dialog()

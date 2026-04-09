import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURAÇÕES DE PÁGINA E CACHE
st.set_page_config(page_title="Financeiro Pro", layout="wide", initial_sidebar_state="collapsed")

# Limpeza de cache para garantir que o Dashboard mude na hora do clique
if 'fluxo_inicial' not in st.session_state:
    st.cache_data.clear()
    st.session_state.fluxo_inicial = True

# --- CONEXÃO COM GOOGLE SHEETS ---
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1epf2H2ZjrmmXrS2OV-8W3P7LC7dp2FKJTHumWNevVeo/edit#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CONFIGURAÇÃO DE TEMA (MODO ESCURO/CLARO) ---
modo_escuro = st.sidebar.toggle("🌙 Modo Escuro", value=False)
COR_PRIMARIA = "#2d6a4f"

if modo_escuro:
    GRADIENTE = "linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%)"
    CARD_BG = "#333333"
    TEXTO = "#ffffff"
    PLOT_THEME = "plotly_dark"
else:
    GRADIENTE = "linear-gradient(135deg, #f8f9fa 0%, #e9f5ec 100%)"
    CARD_BG = "#ffffff"
    TEXTO = "#2c3e50"
    PLOT_THEME = "plotly_white"

# --- CSS CUSTOMIZADO (PARA MANTER A INTERFACE BONITA) ---
st.markdown(f"""
    <style>
    .stApp {{ background: {GRADIENTE}; }}
    h1 {{
        background: linear-gradient(90deg, {COR_PRIMARIA}, #40916c);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 900; text-align: center; font-size: 3rem; margin-bottom: 20px;
    }}
    .card {{
        background-color: {CARD_BG};
        color: {TEXTO};
        padding: 25px;
        border-radius: 20px;
        box-shadow: 0px 10px 20px rgba(0,0,0,0.1);
        text-align: center;
        border: 1px solid rgba(0,0,0,0.05);
    }}
    .stTabs [data-baseweb="tab-list"] {{
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 10px;
        background: transparent;
    }}
    .stTabs [data-baseweb="tab"] {{
        background-color: {CARD_BG};
        color: {TEXTO};
        border-radius: 15px;
        height: 70px;
        font-weight: bold !important;
        font-size: 16px;
        border: 1px solid rgba(0,0,0,0.05);
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {COR_PRIMARIA} !important;
        color: white !important;
        box-shadow: 0px 5px 15px rgba(45, 106, 79, 0.3);
    }}
    </style>
""", unsafe_allow_html=True)

# 2. FUNÇÕES DE PROCESSAMENTO DE DADOS
def carregar_dados(aba, colunas):
    try:
        df = conn.read(spreadsheet=URL_PLANILHA, worksheet=aba, ttl=0)
        if df is not None and not df.empty:
            for col in ['Valor', 'Valor_Aplicado', 'Valor_Objetivo']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            if 'Data' in df.columns:
                df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
            return df
    except: pass
    return pd.DataFrame(columns=colunas)

def salvar_dados(df, aba):
    conn.update(spreadsheet=URL_PLANILHA, worksheet=aba, data=df)
    st.cache_data.clear()

def obter_reserva_config():
    try:
        df_conf = conn.read(spreadsheet=URL_PLANILHA, worksheet='config', ttl=0)
        return float(pd.to_numeric(df_conf.iloc[0, 0], errors='coerce'))
    except: return 0.0

# Inicialização de Colunas e Dados
cols_vendas = ['Data', 'Tipo', 'Categoria', 'Descricao', 'Valor']
cols_invest = ['Data', 'Tipo_Ativo', 'Descricao', 'Valor_Aplicado', 'Taxa_Anual', 'Meta_Destino']
cols_metas = ['Nome_Meta', 'Valor_Objetivo']

df_vendas = carregar_dados('vendas', cols_vendas)
df_invest = carregar_dados('investimentos', cols_invest)
df_metas = carregar_dados('metas', cols_metas)
valor_na_reserva = obter_reserva_config()

# 3. LÓGICA DE CÁLCULOS (ESTA PARTE É CRUCIAL)
# O Saldo da conta é Receitas - Gastos (incluindo o que foi movido para reserva)
total_receitas = df_vendas[df_vendas['Tipo'] == 'Receita']['Valor'].sum() if not df_vendas.empty else 0.0
total_gastos = df_vendas[df_vendas['Tipo'] == 'Gasto']['Valor'].sum() if not df_vendas.empty else 0.0
saldo_disponivel = total_receitas - total_gastos

patrimonio_total = df_invest['Valor_Aplicado'].sum() if not df_invest.empty else 0.0

# 4. INTERFACE VISUAL
st.markdown("<h1>RELATÓRIO FINANCEIRO</h1>", unsafe_allow_html=True)

col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    st.markdown(f"<div class='card'><h5>💰 Saldo Líquido em Conta</h5><h2>R$ {saldo_disponivel:,.2f}</h2></div>", unsafe_allow_html=True)
with col2:
    st.markdown(f"<div class='card'><h5>📈 Patrimônio Investido</h5><h2>R$ {patrimonio_total:,.2f}</h2></div>", unsafe_allow_html=True)
with col3:
    st.markdown(f"<div class='card'><h5>🏦 Reserva</h5><h2>R$ {valor_na_reserva:,.2f}</h2></div>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 DASHBOARD", "📈 CARTEIRA", "🎯 METAS", "📅 ANUAL", "⚙️ AJUSTES"])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.subheader("Análise de Gastos por Categoria")
    df_gastos_only = df_vendas[df_vendas['Tipo'] == 'Gasto']
    if not df_gastos_only.empty:
        fig_donut = px.pie(df_gastos_only, values='Valor', names='Categoria', hole=0.6,
                           color_discrete_sequence=px.colors.sequential.Greens_r)
        fig_donut.update_layout(template=PLOT_THEME, paper_bgcolor='rgba(0,0,0,0)', showlegend=True)
        st.plotly_chart(fig_donut, use_container_width=True)
    else:
        st.info("Lance um gasto para visualizar a distribuição.")

# --- TAB 2: CARTEIRA E APORTE ---
with tab2:
    if valor_na_reserva > 0:
        st.success(f"🎉 Você tem **R$ {valor_na_reserva:,.2f}** prontos para investir!")
        with st.expander("Efetivar Aporte na Carteira", expanded=True):
            c_a, c_b = st.columns(2)
            tipo_sel = c_a.selectbox("Tipo de Ativo", ["Ações", "FIIs", "CDB/Renda Fixa", "Cripto", "Outros"])
            taxa_sel = c_b.number_input("Taxa Estimada Anual (%)", value=12.5)
            nome_sel = st.text_input("Nome do Ativo (Ex: PETR4, Tesouro 2029)")
            meta_sel = st.selectbox("Vincular à Meta:", df_metas['Nome_Meta'].tolist() if not df_metas.empty else ["Geral"])
            
            if st.button("Confirmar Investimento"):
                # 1. Salva na planilha de investimentos real
                novo_item_inv = pd.DataFrame([[str(date.today()), tipo_sel, nome_sel, valor_na_reserva, taxa_sel, meta_sel]], columns=cols_invest)
                salvar_dados(pd.concat([df_invest, novo_item_inv]), 'investimentos')
                # 2. Zera a reserva na config
                conn.update(spreadsheet=URL_PLANILHA, worksheet='config', data=pd.DataFrame([[0.0]], columns=['saldo_aporte']))
                st.rerun()

    st.subheader("Meus Ativos")
    st.dataframe(df_invest, use_container_width=True)

# --- TAB 3: METAS ---
with tab3:
    st.subheader("Objetivos Financeiros")
    if not df_metas.empty:
        for index, row in df_metas.iterrows():
            # Cálculo de progresso baseado na meta vinculada na carteira
            acumulado = df_invest[df_invest['Meta_Destino'] == row['Nome_Meta']]['Valor_Aplicado'].sum()
            porcentagem = min(acumulado / row['Valor_Objetivo'], 1.0) if row['Valor_Objetivo'] > 0 else 0
            
            st.markdown(f"**{row['Nome_Meta']}** - R$ {acumulado:,.2f} de R$ {row['Valor_Objetivo']:,.2f}")
            st.progress(porcentagem)
            st.write(f"{porcentagem*100:.1f}% concluído")
    
    with st.expander("Criar Nova Meta"):
        with st.form("form_metas"):
            n_m = st.text_input("Nome da Meta (Ex: Viagem, Carro)")
            v_m = st.number_input("Valor Alvo", min_value=0.0)
            if st.form_submit_button("Salvar Meta"):
                df_metas = pd.concat([df_metas, pd.DataFrame([[n_m, v_m]], columns=cols_metas)])
                salvar_dados(df_metas, 'metas')
                st.rerun()

# --- TAB 4: EVOLUÇÃO ANUAL ---
with tab4:
    st.subheader("Fluxo de Caixa Mensal")
    if not df_vendas.empty:
        df_vendas['Mes_Ano'] = df_vendas['Data'].dt.strftime('%b/%Y')
        df_agrupado = df_vendas.groupby(['Mes_Ano', 'Tipo'])['Valor'].sum().reset_index()
        fig_evolucao = px.bar(df_agrupado, x='Mes_Ano', y='Valor', color='Tipo', barmode='group',
                             color_discrete_map={'Receita': '#2d6a4f', 'Gasto': '#bc4749'})
        fig_evolucao.update_layout(template=PLOT_THEME, paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_evolucao, use_container_width=True)

# --- TAB 5: AJUSTES E EDIÇÃO ---
with tab5:
    st.subheader("Histórico de Transações")
    df_editado = st.data_editor(df_vendas, num_rows="dynamic", use_container_width=True)
    if st.button("Aplicar Alterações"):
        salvar_dados(df_editado, 'vendas')
        st.rerun()
    
    st.divider()
    if st.button("🗑️ Resetar Todos os Dados", type="primary"):
        salvar_dados(pd.DataFrame(columns=cols_vendas), 'vendas')
        salvar_dados(pd.DataFrame(columns=cols_invest), 'investimentos')
        conn.update(spreadsheet=URL_PLANILHA, worksheet='config', data=pd.DataFrame([[0.0]], columns=['saldo_aporte']))
        st.rerun()

# 5. DIÁLOGO DE LANÇAMENTO (O CORAÇÃO DO ABATIMENTO)
@st.dialog("📝 LANÇAR NOVA TRANSAÇÃO")
def abrir_lancamento():
    tipo_l = st.selectbox("Tipo", ["Receita", "Gasto"])
    cat_l = st.selectbox("Categoria", ["Salário", "Fixo", "Lazer", "Saúde", "Mercado", "Investimento","Variavel","Trabalho"])
    desc_l = st.text_input("Descrição / Título")
    valor_l = st.number_input("Valor (R$)", min_value=0.0, step=10.0)
    data_l = st.date_input("Data", value=date.today())
    
    inv_perc = 0
    if tipo_l == "Receita":
        inv_perc = st.slider("Separar para Investimento (%)", 0, 100, 0)
    
    if st.button("SALVAR NO SISTEMA", use_container_width=True):
        if valor_l > 0:
            novos_itens = []
            # 1. Registro da Transação Principal
            novos_itens.append([str(data_l), tipo_l, cat_l, desc_l, valor_l])
            
            # 2. Lógica de Abatimento se houver Investimento (%)
            if tipo_l == "Receita" and inv_perc > 0:
                valor_para_reserva = (valor_l * inv_perc / 100)
                # CRIAMOS UM GASTO AUTOMÁTICO para abater o saldo da CC imediatamente
                novos_itens.append([str(data_l), "Gasto", "Investimento", f"Reserva de {inv_perc}%", valor_para_reserva])
                
                # Atualizamos a aba config para "lembrar" do dinheiro na Tab 2
                reserva_atual_total = obter_reserva_config() + valor_para_reserva
                conn.update(spreadsheet=URL_PLANILHA, worksheet='config', data=pd.DataFrame([[reserva_atual_total]], columns=['saldo_aporte']))

            # Salva na planilha de vendas
            df_final = pd.concat([df_vendas, pd.DataFrame(novos_itens, columns=cols_vendas)])
            salvar_dados(df_final, 'vendas')
            st.rerun()

st.divider()
if st.button("➕ LANÇAR MOVIMENTAÇÃO", use_container_width=True, type="primary"):
    abrir_lancamento()

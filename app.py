import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURAÇÕES INICIAIS
st.set_page_config(page_title="Financeiro Pro", layout="wide", initial_sidebar_state="collapsed")

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1epf2H2ZjrmmXrS2OV-8W3P7LC7dp2FKJTHumWNevVeo/edit#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- TEMA E CORES ---
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
    h1 {{ background: linear-gradient(90deg, {COR_PRIMARIA}, #40916c); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900; text-align: center; margin-bottom: 20px; }}
    .card {{ background-color: {CARD_BG}; color: {CARD_TEXT}; padding: 20px; border-radius: 15px; box-shadow: 0px 4px 15px rgba(0,0,0,0.1); text-align: center; margin-bottom: 15px; }}
    .stTabs [data-baseweb="tab-list"] {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; }}
    .stTabs [data-baseweb="tab"] {{ background-color: {CARD_BG}; color: {CARD_TEXT}; border-radius: 12px; height: 60px; font-weight: bold !important; }}
    .stTabs [aria-selected="true"] {{ background-color: {COR_PRIMARIA} !important; color: white !important; }}
    </style>
""", unsafe_allow_html=True)

# 2. FUNÇÕES DE DADOS (GOOGLE SHEETS)
def carregar_dados(aba, colunas):
    try:
        df = conn.read(spreadsheet=URL_PLANILHA, worksheet=aba, ttl="0")
        if df is None or df.empty:
            return pd.DataFrame(columns=colunas)
        # Limpeza preventiva de datas ao carregar
        if 'Data' in df.columns:
            df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
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
    try:
        # Criamos o DataFrame garantindo que o nome da coluna é idêntico ao da planilha
        df_conf = pd.DataFrame([{"saldo_aporte": float(valor)}])
        
        # Limpa o cache ANTES para garantir que a conexão está "fresca"
        st.cache_data.clear()
        
        # Grava na aba 'config'
        conn.update(spreadsheet=URL_PLANILHA, worksheet='config', data=df_conf)
        
        # Limpa o cache DEPOIS para o app ler o 0.0 imediatamente
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Erro ao zerar saldo na planilha: {e}")

# Inicialização
cols_trans = ['Data', 'Tipo', 'Categoria', 'Descricao', 'Valor']
cols_inv = ['Data', 'Tipo_Ativo', 'Descricao', 'Valor_Aplicado', 'Taxa_Anual', 'Meta_Destino']
cols_metas = ['Nome_Meta', 'Valor_Objetivo']

df_transacoes = carregar_dados('vendas', cols_trans)
df_invest = carregar_dados('investimentos', cols_inv)
df_metas = carregar_dados('metas', cols_metas)

# 3. DIÁLOGO DE LANÇAMENTO
@st.dialog("📝 NOVO LANÇAMENTO")
def cadastrar_dialog():
    tipo = st.selectbox("Operação", ["Receita", "Gasto"])
    cat = st.selectbox("Categoria", ["Trabalho", "Fixo", "Variável", "Lazer", "Saúde", "Investimento"])
    desc = st.text_input("Descrição")
    valor_in = st.number_input("Valor R$", min_value=0.0)
    data_in = st.date_input("Data", value=date.today())
    
    perc_inv = 0
    if tipo == "Receita":
        perc_inv = st.slider("Investir (%)", 0, 100, 0)
    
    if st.button("CONFIRMAR E SALVAR", use_container_width=True):
        if valor_in > 0:
            nova = pd.DataFrame([[str(data_in), tipo, cat, desc, valor_in]], columns=cols_trans)
            salvar_dados(pd.concat([df_transacoes, nova], ignore_index=True), 'vendas')
            if tipo == "Receita" and perc_inv > 0:
                v_inv = (valor_in * perc_inv) / 100
                salvar_saldo_nuvem(obter_saldo_nuvem() + v_inv)
            st.success("Gravado com sucesso!")
            st.rerun()

# 4. CÁLCULOS TOTAIS
rec = df_transacoes[df_transacoes['Tipo'] == 'Receita']['Valor'].sum()
gas = df_transacoes[df_transacoes['Tipo'] == 'Gasto']['Valor'].sum()
saldo_cc = rec - gas

if not df_invest.empty:
    def calc_atual(row):
        try:
            d = (date.today() - pd.to_datetime(row['Data']).date()).days
            if d <= 0: return row['Valor_Aplicado']
            return row['Valor_Aplicado'] * (1 + ((row['Taxa_Anual']/100)/365))**d
        except: return row['Valor_Aplicado']
    df_invest['Valor_Atualizado'] = df_invest.apply(calc_atual, axis=1)
    total_inv = df_invest['Valor_Atualizado'].sum()
else: total_inv = 0.0

# 5. INTERFACE
st.markdown("<h1>💼 FINANCEIRO</h1>", unsafe_allow_html=True)

col1, col2 = st.columns(2)
col1.markdown(f"<div class='card'><h5>💰 Conta</h5><h2>R$ {saldo_cc:,.2f}</h2></div>", unsafe_allow_html=True)
col2.markdown(f"<div class='card'><h5>📈 Investido</h5><h2>R$ {total_inv:,.2f}</h2></div>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 DASH", "📈 CARTEIRA", "🎯 METAS", "📅 ANUAL", "⚙️ AJUSTES"])

with tab1:
    if not df_transacoes.empty:
        df_g = df_transacoes[df_transacoes['Tipo'] == 'Gasto']
        if not df_g.empty:
            fig = px.pie(df_g, values='Valor', names='Categoria', hole=0.5, color_discrete_sequence=px.colors.sequential.Greens_r)
            fig.update_layout(template=PLOT_THEME, paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

with tab2:
    saldo_reserva = obter_saldo_nuvem()
    if saldo_reserva > 0:
        st.warning(f"💰 Saldo Reservado: **R$ {saldo_reserva:,.2f}**")
        with st.expander("APLICAR AGORA", expanded=True):
            t_at = st.selectbox("Tipo:", ["CDB", "LCA", "FIIs", "Ações"], key="tipo_inv")
            tx_at = st.number_input("Taxa Anual %", value=12.0, key="taxa_inv")
            nm_at = st.text_input("Papel", key="papel_inv")
            m_dest = st.selectbox("Meta:", df_metas['Nome_Meta'].tolist() if not df_metas.empty else ["Geral"], key="meta_inv")
            
            if st.button("✅ Confirmar Aplicação e Zerar Reserva"):
                # 1. Cria o registro do investimento
                novo_investimento = pd.DataFrame([[
                    str(date.today()), t_at, nm_at, saldo_reserva, tx_at, m_dest
                ]], columns=cols_inv)
                
                # 2. Salva o investimento na aba 'investimentos'
                salvar_dados(pd.concat([df_invest, novo_investimento], ignore_index=True), 'investimentos')
                
                # 3. COMANDO CRÍTICO: Zera o saldo na aba 'config'
                salvar_saldo_nuvem(0.0)
                
                st.success("Investimento registrado e saldo zerado!")
                st.rerun()
    else:
        st.info("Não há saldo reservado para novos aportes.")
    
    st.subheader("Minha Carteira")
    st.dataframe(df_invest, use_container_width=True)

with tab3:
    if not df_metas.empty:
        for _, m in df_metas.iterrows():
            acum = df_invest[df_invest['Meta_Destino'] == m['Nome_Meta']]['Valor_Aplicado'].sum() if not df_invest.empty else 0
            st.write(f"**{m['Nome_Meta']}**")
            st.progress(min(acum / m['Valor_Objetivo'], 1.0))
    with st.expander("Nova Meta"):
        n_m = st.text_input("Nome")
        v_m = st.number_input("Alvo", min_value=1.0)
        if st.button("Salvar"):
            salvar_dados(pd.concat([df_metas, pd.DataFrame([[n_m, v_m]], columns=cols_metas)], ignore_index=True), 'metas')
            st.rerun()

with tab4:
    # CORREÇÃO DO ERRO DE DATA AQUI
    if not df_transacoes.empty:
        df_anual = df_transacoes.copy()
        df_anual['Data'] = pd.to_datetime(df_anual['Data'], errors='coerce')
        df_anual = df_anual.dropna(subset=['Data']) # Remove linhas com data inválida
        if not df_anual.empty:
            df_anual['Mes'] = df_anual['Data'].dt.strftime('%b/%Y')
            df_mensal = df_anual.groupby(['Mes', 'Tipo'])['Valor'].sum().reset_index()
            fig_anual = px.bar(df_mensal, x='Mes', y='Valor', color='Tipo', barmode='group')
            fig_anual.update_layout(template=PLOT_THEME, paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_anual, use_container_width=True)

with tab5:
    st.subheader("⚙️ Ajustes")
    with st.expander("📝 Editar Transações"):
        ed_v = st.data_editor(df_transacoes, num_rows="dynamic", use_container_width=True, key="ed_v")
        if st.button("Salvar Transações"): salvar_dados(ed_v, 'vendas'); st.rerun()
    
    st.divider()
    check_limpar = st.checkbox("Desejo apagar tudo.")
    if st.button("LIMPAR TUDO", type="primary", disabled=not check_limpar):
        salvar_dados(pd.DataFrame(columns=cols_trans), 'vendas')
        salvar_dados(pd.DataFrame(columns=cols_inv), 'investimentos')
        salvar_dados(pd.DataFrame(columns=cols_metas), 'metas')
        salvar_saldo_nuvem(0.0)
        st.rerun()

# 6. BOTÃO PRINCIPAL
st.divider()
if st.button("📝 LANÇAR NOVA TRANSAÇÃO", key="btn_gravar", use_container_width=True, type="primary"):
    cadastrar_dialog()

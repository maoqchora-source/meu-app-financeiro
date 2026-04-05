import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import date, datetime

# 1. CONFIGURAÇÕES DE LAYOUT E CORES
st.set_page_config(page_title="Planejamento Financeiro", layout="wide", initial_sidebar_state="collapsed")

# Cores Corporativas
COR_PRIMARIA = '#2d6a4f'  # Verde Escuro
COR_FUNDO = '#f8f9fa'    # Cinza Claro
COR_CARD = '#ffffff'     # Branco
COR_TEXTO = '#2c3e50'    # Grafite

# Injeção de CSS para o novo visual moderno
st.markdown(f"""
    <style>
    /* Fundo principal */
    .stApp {{
        background-color: {COR_FUNDO};
    }}

    /* Estilização dos Títulos */
    h1, h2, h3 {{
        color: {COR_TEXTO} !important;
        font-family: 'Segoe UI', sans-serif;
        text-align: center;
    }}

    /* Métricas em Destaque no Topo */
    [data-testid="stMetricValue"] {{
        color: {COR_PRIMARIA};
        font-size: 3rem !important;
        text-align: center;
    }}
    [data-testid="stMetricLabel"] {{
        text-align: center;
        font-size: 1.2rem !important;
    }}

    /* Container das Abas (Grid) */
    .stTabs [data-baseweb="tab-list"] {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 15px;
        background-color: transparent;
        padding: 0;
        border: none;
    }}

    /* Estilização de cada Aba (Caixa Arredondada) */
    .stTabs [data-baseweb="tab"] {{
        background-color: {COR_CARD};
        color: {COR_TEXTO};
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.05);
        border: 1px solid #e0e0e0;
        transition: transform 0.2s;
        height: auto;
    }}
    .stTabs [data-baseweb="tab"]:hover {{
        transform: translateY(-5px);
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {COR_PRIMARIA} !important;
        color: white !important;
        border: none;
    }}

    /* Botão Gravar Dados Flutuante (FAB) */
    .fab {{
        position: fixed;
        bottom: 30px;
        right: 30px;
        background-color: {COR_PRIMARIA};
        color: white;
        border-radius: 50%;
        width: 60px;
        height: 60px;
        font-size: 30px;
        border: none;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.3);
        cursor: pointer;
        z-index: 1000;
        display: flex;
        align-items: center;
        justify-content: center;
    }}
    .fab:hover {{
        background-color: #1b4332;
    }}

    /* Janela Modal (Popup) */
    [data-testid="stModal"] {{
        background-color: {COR_FUNDO};
        border-radius: 20px;
        padding: 20px;
    }}

    /* Ajustes Gerais */
    .stDataFrame {{
        border-radius: 10px;
        overflow: hidden;
    }}
    </style>
    """, unsafe_allow_html=True)

# 2. FUNÇÕES DE DADOS (Igual às anteriores)
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

# 3. PROCESSAMENTO
if not df_invest.empty:
    df_invest['Valor_Atualizado'] = df_invest.apply(calcular_valor_atual, axis=1)
    total_inv = df_invest['Valor_Atualizado'].sum()
else: total_inv = 0

rec = df_transacoes[df_transacoes['Tipo'] == 'Receita']['Valor'].sum()
gas = df_transacoes[df_transacoes['Tipo'] == 'Gasto']['Valor'].sum()
saldo_cc = rec - gas

# 4. LAYOUT PRINCIPAL
st.title("💼 Planejamento Financeiro")

# Métricas em Duas Linhas no Topo
st.metric("Disponível em Conta", f"R$ {saldo_cc:,.2f}")
st.metric("Patrimônio Investido", f"R$ {total_inv:,.2f}")
st.divider()

# Abas com Ícones e Caixas Arredondadas (Grid 3x2)
# Usando Markdown para renderizar os ícones e texto dentro das abas
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊\nDashboard", 
    "📈\nCarteira", 
    "🎯\nMetas", 
    "📅\nAnual", 
    "⚙️\nAjustes"
])

paleta_corp = [COR_PRIMARIA, '#40916c', '#52b788', '#74c69d', '#95d5b2', '#adb5bd', '#6c757d', '#495057']

with tab1:
    if not df_transacoes.empty:
        df_gasto = df_transacoes[(df_transacoes['Tipo']=='Gasto') & (df_transacoes['Categoria'] != 'Investimento')]
        if not df_gasto.empty:
            fig = px.pie(df_gasto, values='Valor', names='Categoria', hole=0.5, color_discrete_sequence=paleta_corp, title="Gastos Reais (Excluindo Reservas)")
            st.plotly_chart(fig, use_container_width=True)
        st.markdown("### Resumo de Fluxo")
        st.write(f"**Receitas:** R$ {rec:,.2f} | **Saídas/Reservas:** R$ {gas:,.2f}")
    else: st.info("Sem dados.")

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

# 5. BOTÃO FLUTUANTE E JANELA MODAL DE CADASTRO
# Botão FAB usando HTML/CSS
st.markdown('<button class="fab" onclick="document.getElementById(\'modal-cadastro\').style.display=\'block\'">+</button>', unsafe_allow_html=True)

# Janela Modal usando st.experimental_dialog (ou st.modal se disponível em versões mais recentes)
# Para versões do Streamlit que não suportam dialog, usaremos uma aproximação com expander/container
# que abre no topo da tela.

@st.experimental_dialog("📝 Novo Lançamento")
def cadastrar():
    st.write("Preencha as informações abaixo:")
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
            # Lógica de gravação (igual à anterior)
            # Acessando as variáveis globais dentro da função dialog
            global df_transacoes
            
            nova_trans = pd.DataFrame([[data_in, tipo, cat, desc, valor_input]], columns=cols_trans)
            df_transacoes = pd.concat([df_transacoes, nova_trans], ignore_index=True)
            
            if tipo == "Receita" and perc_inv > 0:
                valor_investir = (valor_input * perc_inv) / 100
                trans_ajuste = pd.DataFrame([[data_in, "Gasto", "Investimento", f"Reserva p/ Investir ({desc})", valor_investir]], columns=cols_trans)
                df_transacoes = pd.concat([df_transacoes, trans_ajuste], ignore_index=True)
                atualizar_saldo_aporte(st.session_state.saldo_para_aportar + valor_investir)
            
            salvar_dados(df_transacoes, 'banco_cc.csv')
            st.success("Lançado com sucesso!")
            st.rerun()

# Lógica para abrir a modal quando o botão FAB for clicado
# Como o Streamlit não tem eventos onclick nativos para HTML, usamos uma gambiarra
# com query params para detectar o clique. Mas a forma mais estável no Streamlit Cloud
# é usar um botão nativo estilizado como FAB.

# Vamos usar um botão nativo do Streamlit estilizado como FAB
col1, col2, col3 = st.columns([10, 1, 1]) # Colunas para posicionar o botão à direita
with col2:
    # Botão "+" estilizado com CSS
    if st.button("+", key="fab_button"):
        cadastrar()

# Estilização específica para o botão nativo "+" parecer um FAB
st.markdown("""
    <style>
    div[data-testid="stButton"] button[key="fab_button"] {
        position: fixed;
        bottom: 30px;
        right: 30px;
        background-color: #2d6a4f;
        color: white;
        border-radius: 50%;
        width: 60px;
        height: 60px;
        font-size: 30px;
        border: none;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.3);
        z-index: 1000;
    }
    div[data-testid="stButton"] button[key="fab_button"]:hover {
        background-color: #1b4332;
    }
    </style>
    """, unsafe_allow_html=True)

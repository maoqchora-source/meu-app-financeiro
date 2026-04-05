import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import date, datetime
import webbrowser

# 1. CONFIGURAÇÕES E BANCO DE DADOS
st.set_page_config(page_title="Finanças Mobile Pro", layout="wide", initial_sidebar_state="collapsed")

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

# Definição das colunas oficiais
cols_trans = ['Data', 'Tipo', 'Categoria', 'Descricao', 'Valor']
cols_inv = ['Data', 'Tipo_Ativo', 'Descricao', 'Valor_Aplicado', 'Taxa_Anual', 'Meta_Destino']
cols_metas = ['Nome_Meta', 'Valor_Objetivo']

# Inicialização
df_transacoes = carregar_dados('banco_cc.csv', cols_trans)
df_invest = carregar_dados('investimentos.csv', cols_inv)
df_metas = carregar_dados('metas.csv', cols_metas)

if 'saldo_para_aportar' not in st.session_state:
    st.session_state.saldo_para_aportar = 0.0

# 2. LÓGICA DE RENDIMENTO
def calcular_valor_atual(row):
    try:
        data_inv = row['Data']
        if isinstance(data_inv, str):
            data_inv = datetime.strptime(data_inv, '%Y-%m-%d').date()
        dias = (date.today() - data_inv).days
        if dias <= 0: return row['Valor_Aplicado']
        taxa_diaria = (1 + (row['Taxa_Anual']/100))**(1/365) - 1
        return row['Valor_Aplicado'] * (1 + taxa_diaria)**dias
    except: return row['Valor_Aplicado']

# 3. SIDEBAR (CADASTRO)
with st.sidebar:
    st.header("📲 Novo Lançamento")
    tipo = st.selectbox("Operação", ["Receita", "Gasto"])
    cat = st.selectbox("Categoria", ["Trabalho", "Fixo", "Variável", "Lazer", "Saúde"])
    desc = st.text_input("Descrição")
    valor = st.number_input("Valor R$", min_value=0.0)
    data_in = st.date_input("Data")
    
    perc_inv = 0
    if tipo == "Receita":
        perc_inv = st.slider("Investir (%)", 0, 100, 10)
    
    if st.button("🚀 GRAVAR"):
        nova_trans = pd.DataFrame([[data_in, tipo, cat, desc, valor]], columns=cols_trans)
        df_transacoes = pd.concat([df_transacoes, nova_trans], ignore_index=True)
        if tipo == "Receita" and perc_inv > 0:
            st.session_state.saldo_para_aportar += (valor * perc_inv) / 100
        salvar_dados(df_transacoes, 'banco_cc.csv')
        st.success("Salvo!")
        st.rerun()

# 4. PROCESSAMENTO
if not df_invest.empty:
    df_invest['Valor_Atualizado'] = df_invest.apply(calcular_valor_atual, axis=1)
    total_inv = df_invest['Valor_Atualizado'].sum()
else: total_inv = 0

rec = df_transacoes[df_transacoes['Tipo'] == 'Receita']['Valor'].sum()
gas = df_transacoes[df_transacoes['Tipo'] == 'Gasto']['Valor'].sum()
saldo_cc = rec - gas

# 5. LAYOUT DE ABAS
st.title("💎 Finanças Pro")
c1, c2 = st.columns(2)
c1.metric("Banco CC", f"R$ {saldo_cc:,.2f}")
c2.metric("Investido", f"R$ {total_inv:,.2f}")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dash", "📈 Ativos", "🎯 Metas", "📅 Anual", "⚙️ Ajustes"])

with tab1:
    if not df_transacoes.empty:
        df_gasto = df_transacoes[df_transacoes['Tipo']=='Gasto']
        if not df_gasto.empty:
            fig = px.pie(df_gasto, values='Valor', names='Categoria', hole=0.4, title="Meus Gastos")
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("Grave um 'Gasto' para ver o gráfico.")
    else: st.info("Sem movimentações.")

with tab2:
    st.subheader("💰 Carteira")
    if st.session_state.saldo_para_aportar > 0:
        st.warning(f"Disponível: R$ {st.session_state.saldo_para_aportar:,.2f}")
        col_a, col_b = st.columns(2)
        t_at = col_a.selectbox("Tipo:", ["CDI", "LCA", "FIIs", "Ações"])
        tx_at = col_b.number_input("Taxa Anual %", value=12.0)
        nm_at = st.text_input("Nome do Papel")
        m_dest = st.selectbox("Destinar p/ Meta:", df_metas['Nome_Meta'].tolist() if not df_metas.empty else ["Geral"])
        
        if st.button("Confirmar Investimento"):
            novo = pd.DataFrame([[date.today(), t_at, nm_at, st.session_state.saldo_para_aportar, tx_at, m_dest]], columns=cols_inv)
            df_invest = pd.concat([df_invest, novo], ignore_index=True)
            salvar_dados(df_invest, 'investimentos.csv')
            st.session_state.saldo_para_aportar = 0
            st.rerun()
    
    st.divider()
    if not df_invest.empty:
        for i, row in df_invest.iterrows():
            with st.expander(f"{row['Tipo_Ativo']} - {row['Descricao']}"):
                st.write(f"**Valor Atual:** R$ {row['Valor_Atualizado']:,.2f}")
                st.write(f"**Meta:** {row['Meta_Destino']}")

with tab3:
    st.subheader("🚩 Minhas Metas")
    with st.expander("➕ Criar Nova Meta"):
        n_meta = st.text_input("Nome (Ex: Viagem)")
        v_meta = st.number_input("Valor Objetivo R$", min_value=1.0)
        if st.button("Salvar Meta"):
            if n_meta:
                nova_m = pd.DataFrame([[n_meta, v_meta]], columns=cols_metas)
                df_metas = pd.concat([df_metas, nova_m], ignore_index=True)
                salvar_dados(df_metas, 'metas.csv')
                st.success("Meta criada!")
                st.rerun()

    st.divider()
    if not df_metas.empty:
        for i, m in df_metas.iterrows():
            acumulado = df_invest[df_invest['Meta_Destino'] == m['Nome_Meta']]['Valor_Atualizado'].sum() if not df_invest.empty else 0
            progresso = min(acumulado / m['Valor_Objetivo'], 1.0)
            st.write(f"**{m['Nome_Meta']}**")
            st.progress(progresso)
            st.write(f"R$ {acumulado:,.2f} de R$ {m['Valor_Objetivo']:,.2f} ({progresso*100:.1f}%)")

with tab4:
    if not df_transacoes.empty:
        df_transacoes['Data'] = pd.to_datetime(df_transacoes['Data'])
        df_transacoes['Mes'] = df_transacoes['Data'].dt.strftime('%b/%Y')
        df_mensal = df_transacoes.groupby(['Mes', 'Tipo'])['Valor'].sum().reset_index()
        fig_anual = px.bar(df_mensal, x='Mes', y='Valor', color='Tipo', barmode='group', title="Evolução Mensal")
        st.plotly_chart(fig_anual, use_container_width=True)

with tab5:
    st.subheader("🛠️ Gestão de Dados")
    
    # EDITAR BANCO CC
    with st.expander("✏️ Editar/Excluir Transações (Banco CC)"):
        if not df_transacoes.empty:
            # st.data_editor cria uma tabela editável na tela!
            df_trans_editada = st.data_editor(df_transacoes, num_rows="dynamic", use_container_width=True, key="editor_trans")
            if st.button("💾 Salvar Alterações no Banco"):
                salvar_dados(df_trans_editada, 'banco_cc.csv')
                st.success("Banco de transações atualizado!")
                st.rerun()
        else: st.info("Nenhuma transação para editar.")

    # EDITAR INVESTIMENTOS
    with st.expander("✏️ Editar/Excluir Investimentos"):
        if not df_invest.empty:
            df_inv_editada = st.data_editor(df_invest, num_rows="dynamic", use_container_width=True, key="editor_inv")
            if st.button("💾 Salvar Alterações nos Ativos"):
                salvar_dados(df_inv_editada, 'investimentos.csv')
                st.success("Investimentos atualizados!")
                st.rerun()
        else: st.info("Nenhum investimento para editar.")

    st.divider()
    
    # LIMPAR TUDO (RESTAURAR)
    st.error("💣 ZONA DE PERIGO")
    if st.button("🚨 LIMPAR TUDO E REINICIAR APP"):
        # Apagar os arquivos físicos
        for arq in ['banco_cc.csv', 'investimentos.csv', 'metas.csv']:
            if os.path.exists(arq):
                os.remove(arq)
        st.session_state.saldo_para_aportar = 0.0
        st.warning("Todos os dados foram apagados. Recarregando...")
        st.rerun()

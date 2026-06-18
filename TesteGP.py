import streamlit as st
import pandas as pd
import plotly.express as px

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Dashboard Google Sheets", layout="wide")

st.title("Gestão de GPs X Clientes e Ordens de Serviço (via Google Sheets)")
#st.markdown("Conectado em tempo real com as suas Google Planilhas.")

# ==========================================
# CONFIGURAÇÃO DOS IDs DAS PLANILHAS
# ==========================================
# 1. Planilha de Clientes por GP (A que você já tinha)
ID_PLANILHA_CLIENTES = '1jQkoDfW438MtuGaTsoBrO_sNk-oj2Zwp0UXeBohJeCg'

# 2. Cole aqui o ID da sua NOVA planilha de Ordens de Serviço (OS)
ID_PLANILHA_OS = '1u9TH6RpD8F9-ImM5KR8dknCmxvs0_QjD' 

# Lista manual de GPs (conforme seu código original)
lista_gps = ["Fausto", "MauricioOrtiga", "MauricioFavero", "Cristiane", "Jaciara""Nasare", "Jhonanthan"] 

# ==========================================
# FUNÇÕES DE CARREGAMENTO DE DADOS (COM CACHE)
# ==========================================
@st.cache_data(ttl=10) # Atualiza a cada 10 segundos
def carregar_dados_gp(id_planilha, nome_aba):
    url_csv = f"https://docs.google.com/spreadsheets/d/{id_planilha}/gviz/tq?tqx=out:csv&sheet={nome_aba}"
    return pd.read_csv(url_csv)

@st.cache_data(ttl=10)
def carregar_dados_os(id_planilha):
    url_csv = f"https://docs.google.com/spreadsheets/d/{id_planilha}/gviz/tq?tqx=out:csv"
    df = pd.read_csv(url_csv)
    # Limpa espaços extras nos nomes das colunas
    df.columns = df.columns.str.strip()
    return df

# ==========================================
# BARRA LATERAL - FILTROS
# ==========================================
st.sidebar.header("Filtros")

# Filtro 1: Seleção do GP
gp_selecionado = st.sidebar.selectbox("Selecione o Gerente de Projeto (GP):", lista_gps)

try:
    # 1. Carrega os dados de ambas as planilhas
    df_clientes = carregar_dados_gp(ID_PLANILHA_CLIENTES, gp_selecionado)
    df_os = carregar_dados_os(ID_PLANILHA_OS)
    
    # 2. Identifica as colunas de Cliente (B) e Status (H) na planilha de OS
    col_cliente = 'nomecliente' if 'nomecliente' in df_os.columns else df_os.columns[1]
    col_status = 'status' if 'status' in df_os.columns else df_os.columns[7]
    
    # 3. Tratamento de correspondência flexível de nomes (Planilha 1 vs Planilha 2)
    lista_clientes_do_gp = df_clientes.iloc[:, 0].dropna().unique()
    lista_clientes_limpa = [str(c).strip().lower() for c in lista_clientes_do_gp]
    
    def cliente_pertence_ao_gp(nome_os):
        if pd.isna(nome_os):
            return False
        nome_os_limpo = str(nome_os).strip().lower()
        for c_gp in lista_clientes_limpa:
            if c_gp in nome_os_limpo or nome_os_limpo in c_gp:
                return True
        return False

    # Filtra as OS do GP
    df_os_filtrado_gp = df_os[df_os[col_cliente].apply(cliente_pertence_ao_gp)]

    # Filtro 2: Seleção do Cliente (Geral vs Específico)
    opcoes_clientes = ["Todos os Clientes (Geral)"] + sorted(list(lista_clientes_do_gp))
    cliente_selecionado = st.sidebar.selectbox("Selecione o Cliente para análise de OS:", opcoes_clientes)

    # 4. Aplica o filtro final com base na escolha do usuário
    if cliente_selecionado == "Todos os Clientes (Geral)":
        df_os_final = df_os_filtrado_gp
    else:
        nome_sel_limpo = str(cliente_selecionado).strip().lower()
        df_os_final = df_os_filtrado_gp[
            df_os_filtrado_gp[col_cliente].astype(str).str.strip().str.lower().str.contains(nome_sel_limpo) |
            df_os_filtrado_gp[col_cliente].astype(str).str.strip().str.lower().apply(lambda x: x in nome_sel_limpo)
        ]

    # ==========================================
    # BLOCOS DE EXIBIÇÃO DO DASHBOARD
    # ==========================================
    st.subheader(f"Carteira de Clientes: {gp_selecionado}")
    
    # Indicadores em cartões (Métricas)
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Total de Clientes do GP", value=len(df_clientes))
    with col2:
        st.metric(label=f"Total de OS Relacionadas ({cliente_selecionado})", value=len(df_os_final))

    st.write("---")
    st.subheader(f"Análise de Ordens de Serviço: {cliente_selecionado}")

    if len(df_os_final) > 0:
        
        # LÓGICA DE CONDICIONAL DOS GRÁFICOS
        if cliente_selecionado == "Todos os Clientes (Geral)":
            # Modo Geral: Mostra os dois gráficos lado a lado em colunas
            graf1, graf2 = st.columns(2)

            with graf1:
                st.markdown("#### Volumetria de OS por Cliente")
                fig_pizza = px.pie(df_os_final, names=col_cliente, title="Distribuição de OS por Cliente")
                fig_pizza.update_traces(textinfo='percent+value', textposition='inside')
                st.plotly_chart(fig_pizza, use_container_width=True)

            with graf2:
                st.markdown("#### Status Geral das Ordens de Serviço")
                df_barras = df_os_final.groupby([col_status]).size().reset_index(name='Quantidade')
                fig_barras = px.bar(df_barras, x=col_status, y='Quantidade', 
                                    title="Quantidade de OS por Status",
                                    labels={col_status: 'Status', 'Quantidade': 'Total de OS'},
                                    color=col_status,
                                    text='Quantidade')
                fig_barras.update_traces(textposition='outside')
                st.plotly_chart(fig_barras, use_container_width=True)
        
        else:
            # Modo Específico: Não cria colunas, o gráfico de barras ocupa a tela inteira (100% de largura)
            st.markdown(f"#### Status das Ordens de Serviço — {cliente_selecionado}")
            df_barras = df_os_final.groupby([col_status]).size().reset_index(name='Quantidade')
            fig_barras = px.bar(df_barras, x=col_status, y='Quantidade', 
                                title=f"Quantidade de OS por Status para {cliente_selecionado}",
                                labels={col_status: 'Status', 'Quantidade': 'Total de OS'},
                                color=col_status,
                                text='Quantidade')
            fig_barras.update_traces(textposition='outside')
            st.plotly_chart(fig_barras, use_container_width=True) # Ocupa a tela cheia de forma limpa
                      
    else:
        st.info("Nenhuma Ordem de Serviço encontrada para as condições selecionadas.")

    # Tabela original da carteira de clientes
    st.write("---")
    st.write("### Listagem de Clientes do GP")
    st.dataframe(df_clientes, use_container_width=True)

except Exception as e:
    st.error(f"Erro ao processar os dados: {e}")
    st.info("Dicas de Resolução:\n"
            "1. Lembre-se de preencher a variável ID_PLANILHA_OS com o ID da nova planilha.\n"
            "2. Certifique-se de que a nova planilha esteja configurada para 'Qualquer pessoa com o link'.\n"
            "3. Caso rode no computador local, verifique se instalou o Plotly usando: pip install plotly")
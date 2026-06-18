import streamlit as st
import pandas as pd
import plotly.express as px

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Dashboard Google Sheets", layout="wide")

st.title(":blue[Gestão de GPs X Clientes e Ordens de Serviço (via Google Sheets)]")

# ==========================================
# CONFIGURAÇÃO DOS IDs DAS PLANILHAS
# ==========================================
ID_PLANILHA_CLIENTES = '1jQkoDfW438MtuGaTsoBrO_sNk-oj2Zwp0UXeBohJeCg'
ID_PLANILHA_OS = '1u9TH6RpD8F9-ImM5KR8dknCmxvs0_QjD' 

# Lista manual de GPs (Corrigido o espaçamento em "Jaciara", "Nasare")
lista_gps = ["Fausto", "MauricioOrtiga", "MauricioFavero", "Cristiane", "Jaciara", "Nasare", "Jhonanthan"] 

# ==========================================
# FUNÇÕES DE CARREGAMENTO DE DADOS (COM CACHE)
# ==========================================
@st.cache_data(ttl=10)
def carregar_dados_gp(id_planilha, nome_aba):
    url_csv = f"https://docs.google.com/spreadsheets/d/{id_planilha}/gviz/tq?tqx=out:csv&sheet={nome_aba}"
    return pd.read_csv(url_csv)

@st.cache_data(ttl=10)
def carregar_dados_os(id_planilha):
    url_csv = f"https://docs.google.com/spreadsheets/d/{id_planilha}/gviz/tq?tqx=out:csv"
    df = pd.read_csv(url_csv)
    df.columns = df.columns.str.strip()
    return df

# ==========================================
# BARRA LATERAL - FILTROS
# ==========================================
st.sidebar.header("Filtros")
gp_selecionado = st.sidebar.selectbox("Selecione o Gerente de Projeto (GP):", lista_gps)

try:
    df_clientes = carregar_dados_gp(ID_PLANILHA_CLIENTES, gp_selecionado)
    df_os = carregar_dados_os(ID_PLANILHA_OS)
    
    col_cliente = 'nomecliente' if 'nomecliente' in df_os.columns else df_os.columns[1]
    col_status = 'status' if 'status' in df_os.columns else df_os.columns[7]
    
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

    df_os_filtrado_gp = df_os[df_os[col_cliente].apply(cliente_pertence_ao_gp)]

    opcoes_clientes = ["Todos os Clientes (Geral)"] + sorted(list(lista_clientes_do_gp))
    cliente_selecionado = st.sidebar.selectbox("Selecione o Cliente para análise de OS:", opcoes_clientes)

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
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Total de Clientes do GP", value=len(df_clientes))
    with col2:
        st.metric(label=f"Total de OS Relacionadas ({cliente_selecionado})", value=len(df_os_final))

    st.write("---")
    st.subheader(f"Análise de Ordens de Serviço: {cliente_selecionado}")

    if len(df_os_final) > 0:
        
        if cliente_selecionado == "Todos os Clientes (Geral)":
            # Agrupa e ordena os clientes pela quantidade de OS (Maior para Menor)
            df_volumetria = df_os_final.groupby(col_cliente).size().reset_index(name='Quantidade')
            df_volumetria = df_volumetria.sort_values(by='Quantidade', ascending=False)
            
            graf1, graf2 = st.columns(2)

            with graf1:
                # 1. GRÁFICO DE PIZZA: Mostra SEMPRE apenas o Top 10 para não poluir
                st.markdown("#### Top 10 Clientes com Maior Volume de OS")
                df_top10 = df_volumetria.head(10)
                fig_pizza_top = px.pie(df_top10, values='Quantidade', names=col_cliente, 
                                       title="Os 10 maiores clientes em volume de OS")
                fig_pizza_top.update_traces(textinfo='percent+value', textposition='inside')
                st.plotly_chart(fig_pizza_top, use_container_width=True)
                
                st.write("---")
                
                # 2. GRÁFICO DE BARRAS: Mostra a lista completa (com scroll vertical automático se for grande)
                st.markdown("#### Volumetria Completa por Cliente")
                
                # Inverte a ordem para as barras maiores ficarem no topo do gráfico horizontal
                df_barras_completo = df_volumetria.sort_values(by='Quantidade', ascending=True)
                
                fig_barras_clientes = px.bar(
                    df_barras_completo, 
                    x='Quantidade', 
                    y=col_cliente, 
                    orientation='h',
                    title="Distribuição Geral de todas as OS por Cliente",
                    text='Quantidade'
                )
                
                # Ajusta a altura dinamicamente baseado no número de clientes para criar o scroll na tela
                altura_dinamica = max(400, len(df_barras_completo) * 25)
                fig_barras_clientes.update_layout(
                    height=altura_dinamica, 
                    yaxis={'type': 'category'}
                )
                fig_barras_clientes.update_traces(textposition='outside')
                st.plotly_chart(fig_barras_clientes, use_container_width=True)

            with graf2:
                # Mantém o seu gráfico original de Status do lado direito
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
            # Modo Específico (Filtro de cliente único)
            st.markdown(f"#### Status das Ordens de Serviço — {cliente_selecionado}")
            df_barras = df_os_final.groupby([col_status]).size().reset_index(name='Quantidade')
            fig_barras = px.bar(df_barras, x=col_status, y='Quantidade', 
                                title=f"Quantidade de OS por Status para {cliente_selecionado}",
                                labels={col_status: 'Status', 'Quantidade': 'Total de OS'},
                                color=col_status,
                                text='Quantidade')
            fig_barras.update_traces(textposition='outside')
            st.plotly_chart(fig_barras, use_container_width=True)
                      
    else:
        st.info("Nenhuma Ordem de Serviço encontrada para as condições selecionadas.")

    st.write("---")
    st.write("### Listagem de Clientes do GP")
    
    # Seleciona apenas a primeira coluna e remove linhas completamente vazias
    df_exibicao = df_clientes.iloc[:, [0]].dropna()

    st.dataframe(df_exibicao, use_container_width=True)

except Exception as e:
    st.error(f"Erro ao processar os dados: {e}")
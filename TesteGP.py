import streamlit as st
import pandas as pd
import plotly.express as px

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Dashboard Google Sheets", layout="wide")

st.title(":red[Análise de GPs, Clientes e Ordens de Serviço]")

# Inicializa o estado do fluxo caso não exista
if 'tela' not in st.session_state:
    st.session_state.tela = 'selecao'

# ==========================================
# CONFIGURAÇÃO DOS IDs DAS PLANILHAS
# ==========================================
ID_PLANILHA_CLIENTES = '1jQkoDfW438MtuGaTsoBrO_sNk-oj2Zwp0UXeBohJeCg'
ID_PLANILHA_OS = '1u9TH6RpD8F9-ImM5KR8dknCmxvs0_QjD' 

lista_gps = ["Fausto", "Mauricio_Ortiga", "Mauricio_Favero", "Cristiane", "Jaciara", "Nasare", "Jhonanthan"] 

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
# FLUXO TELA 1: SELEÇÃO MÚLTIPLA NA TABELA
# ==========================================
if st.session_state.tela == 'selecao':
    gp_selecionado = st.selectbox("Selecione o Gerente de Projeto (GP):", lista_gps)

    try:
        df_clientes = carregar_dados_gp(ID_PLANILHA_CLIENTES, gp_selecionado)
        
        st.write("---")
        st.subheader("Selecione um ou mais clientes na tabela abaixo:")
        
        # Isola a primeira coluna e limpa linhas vazias (Sem adicionar linha "Todos os Clientes")
        df_exibicao = df_clientes.iloc[:, [0]].dropna()
        nome_coluna_cliente = df_exibicao.columns[0]

        # Tabela interativa com seleção múltipla ativa
        selecao_tabela = st.dataframe(
            df_exibicao, 
            use_container_width=True,
            on_select="rerun",
            selection_mode="multi-row"
        )

        # Processa as linhas que estão marcadas no momento
        if selecao_tabela and selecao_tabela["selection"]["rows"]:
            linhas_selecionadas = selecao_tabela["selection"]["rows"]
            clientes_escolhidos = df_exibicao.iloc[linhas_selecionadas, 0].tolist()
            
            st.write(f"Clientes selecionados: {', '.join(clientes_escolhidos)}")
            
            # Botão para confirmar o envio após marcar o escopo desejado
            if st.button("Gerar Gráficos dos Selecionados", type="primary", use_container_width=True):
                st.session_state.gp_atual = gp_selecionado
                st.session_state.cliente_atual = clientes_escolhidos
                st.session_state.tela = 'graficos'
                st.rerun()
        else:
            st.info("Selecione pelo menos uma linha na tabela acima para habilitar o botão de gráficos.")

    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")

# ==========================================
# FLUXO TELA 2: EXIBIÇÃO DE TODOS OS GRÁFICOS
# ==========================================
elif st.session_state.tela == 'graficos':
    gp_selecionado = st.session_state.gp_atual
    clientes_selecionados = st.session_state.cliente_atual

    # Define o texto do cabeçalho baseado na quantidade de clientes selecionados
    if len(clientes_selecionados) == 1:
        texto_dashboard = clientes_selecionados[0]
    else:
        texto_dashboard = f"Filtro Combinado ({len(clientes_selecionados)} Clientes)"

    head1, head2 = st.columns([5, 1])
    with head1:
        st.subheader(f"Dashboard: {gp_selecionado} -> {texto_dashboard}")
    with head2:
        if st.button("Mudar Filtros", use_container_width=True, type="primary"):
            st.session_state.tela = 'selecao'
            st.rerun()

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

        # Filtra todas as OS que coincidam com qualquer um dos clientes selecionados
        mascaras = []
        for cli in clientes_selecionados:
            nome_sel_limpo = str(cli).strip().lower()
            mascaras.append(
                df_os_filtrado_gp[col_cliente].astype(str).str.strip().str.lower().str.contains(nome_sel_limpo) |
                df_os_filtrado_gp[col_cliente].astype(str).str.strip().str.lower().apply(lambda x: x in nome_sel_limpo)
            )
        df_os_final = df_os_filtrado_gp[pd.concat(mascaras, axis=1).any(axis=1)]

        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="Total de Clientes do GP", value=len(df_clientes))
        with col2:
            st.metric(label="Total de OS Relacionadas", value=len(df_os_final))

        st.write("---")

        if len(df_os_final) > 0:
            # Agrupa e ordena os dados para a estrutura de volumetria
            df_volumetria = df_os_final.groupby(col_cliente).size().reset_index(name='Quantidade')
            df_volumetria = df_volumetria.sort_values(by='Quantidade', ascending=False)
            
            graf1, graf2 = st.columns(2)

            with graf1:
                # 1. Gráfico de Pizza (Mostra os maiores volumes do escopo selecionado)
                
                df_top20 = df_volumetria.head(20)
                fig_pizza_top = px.pie(df_top20, values='Quantidade', names=col_cliente, 
                                       title="Distribuição de volume de OS por cliente (Top 20)")
                fig_pizza_top.update_traces(textinfo='percent+value', textposition='inside')
                st.plotly_chart(fig_pizza_top, use_container_width=True)
                
                st.write("---")
                
                # 2. Gráfico de Barras Horizontais (Volumetria completa por cliente)
                
                df_barras_completo = df_volumetria.sort_values(by='Quantidade', ascending=True)
                
                fig_barras_clientes = px.bar(
                    df_barras_completo, 
                    x='Quantidade', 
                    y=col_cliente, 
                    orientation='h',
                    title="Quantidade total de OS por cliente",
                    text='Quantidade'
                )
                
                altura_dinamica = max(400, len(df_barras_completo) * 25)
                fig_barras_clientes.update_layout(height=altura_dinamica, yaxis={'type': 'category'})
                fig_barras_clientes.update_traces(textposition='outside')
                st.plotly_chart(fig_barras_clientes, use_container_width=True)

            with graf2:
                # 3. Gráfico de Barras Verticais (Status das Ordens de Serviço do escopo selecionado)
                
                df_barras = df_os_final.groupby([col_status]).size().reset_index(name='Quantidade')
                fig_barras = px.bar(df_barras, x=col_status, y='Quantidade', 
                                    title="Quantidade de OS por Status",
                                    labels={col_status: 'Status', 'Quantidade': 'Total de OS'},
                                    color=col_status,
                                    text='Quantidade')
                fig_barras.update_traces(textposition='outside')
                st.plotly_chart(fig_barras, use_container_width=True)
                          
        else:
            st.info("Nenhuma Ordem de Serviço encontrada para as condições selecionadas.")

    except Exception as e:
        st.error(f"Erro ao processar os dados: {e}")
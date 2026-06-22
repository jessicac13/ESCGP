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

# Carrega a planilha de OS logo no início para o relatório central
try:
    df_os_geral = carregar_dados_os(ID_PLANILHA_OS)
except Exception as e:
    st.error(f"Erro ao carregar planilha de OS: {e}")
    df_os_geral = pd.DataFrame()

# Mapeia dinamicamente a coluna de cliente na planilha de OS
if not df_os_geral.empty:
    col_cliente = 'nomecliente' if 'nomecliente' in df_os_geral.columns else df_os_geral.columns[1]
    # Mapeia a coluna C (Índice 2) para o Grupo de Clientes
    col_grupo_cliente = df_os_geral.columns[2] if len(df_os_geral.columns) > 2 else None
else:
    col_cliente = None
    col_grupo_cliente = None

# ==========================================
# SIDEBAR: FILTROS NA LATERAL
# ==========================================
with st.sidebar:
    st.header("Filtros de Escopo")
    gp_selecionado = st.selectbox("Selecione o Gerente de Projeto (GP):", lista_gps)

    clientes_escolhidos = []
    try:
        df_clientes = carregar_dados_gp(ID_PLANILHA_CLIENTES, gp_selecionado)
        df_exibicao = df_clientes.iloc[:, [0]].dropna()
        
        st.subheader("Selecione os clientes:")
        selecao_tabela = st.dataframe(
            df_exibicao, 
            use_container_width=True,
            on_select="rerun",
            selection_mode="multi-row"
        )

        if selecao_tabela and selecao_tabela["selection"]["rows"]:
            linhas_selecionadas = selecao_tabela["selection"]["rows"]
            clientes_escolhidos = df_exibicao.iloc[linhas_selecionadas, 0].tolist()
            st.caption(f"**Selecionados:** {', '.join(clientes_escolhidos)}")
    except Exception as e:
        st.error(f"Erro ao carregar clientes do GP: {e}")

    st.write("---")
    
    # Botão de Gerar/Mudar Gráficos baseado no estado atual
    if st.session_state.tela == 'selecao':
        if clientes_escolhidos:
            if st.button("Gerar Gráficos", type="primary", use_container_width=True):
                st.session_state.gp_atual = gp_selecionado
                st.session_state.cliente_atual = clientes_escolhidos
                st.session_state.tela = 'graficos'
                st.rerun()
        else:
            st.info("Selecione ao menos um cliente na tabela para liberar os gráficos.")
    else:
        if st.button("Voltar ao Relatório Geral", type="secondary", use_container_width=True):
            st.session_state.tela = 'selecao'
            st.rerun()


# ==========================================
# PAINEL CENTRAL: EXIBIÇÃO DINÂMICA
# ==========================================

# TELA 1: RELATÓRIO GLOBAL (Antes de clicar em gerar)
if st.session_state.tela == 'selecao':
    
    # --- NOVA SEÇÃO: DETECÇÃO DE CLIENTES SEM GP ---
    st.subheader("⚠️ Clientes Sem GP Atribuído")
    
    if not df_os_geral.empty and col_cliente:
        try:
            # 1. Cria uma lista consolidada de todos os clientes que pertencem a ALGUM GP
            todos_clientes_com_gp = set()
            for gp in lista_gps:
                try:
                    df_aux = carregar_dados_gp(ID_PLANILHA_CLIENTES, gp)
                    if not df_aux.empty:
                        # Pega a primeira coluna de clientes de cada aba e padroniza o texto
                        clientes_gp = df_aux.iloc[:, 0].dropna().astype(str).str.strip().str.lower().tolist()
                        todos_clientes_com_gp.update(clientes_gp)
                except Exception:
                    pass # Se uma aba falhar, pula para a próxima para não travar o app
            
            # 2. Pega todos os clientes únicos que possuem OS registradas
            clientes_com_os = df_os_geral[col_cliente].dropna().unique()
            
            # 3. Descobre quais clientes têm OS mas não estão mapeados em nenhum GP
            clientes_orfaos_dados = []
            for cli in clientes_com_os:
                cli_limpo = str(cli).strip()
                cli_lower = cli_limpo.lower()
                
                # Verifica se o cliente da OS NÃO bate com nenhuma parte dos cadastrados dos GPs
                if not any(c_gp in cli_lower or cli_lower in c_gp for c_gp in todos_clientes_com_gp):
                    # Conta quantas OS esse cliente sem GP possui no sistema
                    qtd_os_orfa = len(df_os_geral[df_os_geral[col_cliente] == cli])
                    clientes_orfaos_dados.append({
                        "Cliente Sem GP": cli_limpo,
                        "Quantidade de OS": qtd_os_orfa
                    })
            
            # 4. Exibe os resultados em tela
            if clientes_orfaos_dados:
                df_orfaos = pd.DataFrame(clientes_orfaos_dados).sort_values(by="Quantidade de OS", ascending=False)
                
                # Alerta visual com a métrica
                st.error(f"Foram encontrados {len(df_orfaos)} clientes com Ordens de Serviço ativas que não estão na carteira de nenhum GP listado.")
                
                # Mostra a tabela expandível para não poluir a tela se a lista for muito grande
                with st.expander("Clique aqui para ver a lista completa de clientes sem GP", expanded=True):
                    st.dataframe(df_orfaos, use_container_width=True, hide_index=True)
            else:
                st.success("Tudo certo! Todos os clientes com OS ativas estão atribuídos a pelo menos um GP.")
                
        except Exception as e:
            st.warning(f"Não foi possível processar a auditoria de clientes sem GP: {e}")
            
    st.write("---")
    
    # --- NOVA SEÇÃO VISUAL: DISTRIBUIÇÃO GLOBAL POR GRUPO DE CLIENTE ---
    if not df_os_geral.empty and col_grupo_cliente:
        st.subheader("Relatório Geral: Distribuição por Grupo de Cliente")
        try:
            df_grupos = df_os_geral.groupby(col_grupo_cliente).size().reset_index(name='Qtd OS')
            df_grupos = df_grupos.sort_values(by='Qtd OS', ascending=False)
            
            c1_g, c2_g = st.columns([1, 2])
            with c1_g:
                st.dataframe(df_grupos, use_container_width=True, hide_index=True)
            with c2_g:
                fig_pizza_grupo = px.pie(
                    df_grupos, 
                    values='Qtd OS', 
                    names=col_grupo_cliente, 
                    title="Porcentagem de OS por Grupo de Cliente (Coluna C)"
                )
                fig_pizza_grupo.update_traces(textinfo='percent+value', textposition='inside')
                st.plotly_chart(fig_pizza_grupo, use_container_width=True)
        except Exception as e:
            st.error(f"Erro ao gerar gráfico de Grupos de Cliente: {e}")
            
    st.write("---")
    
    # Relatório de cargos original (movido para baixo da auditoria de clientes)
    st.subheader("Relatório Geral: Quantidade de OS por Cargo")
    if not df_os_geral.empty:
        try:
            nome_coluna_cargo = df_os_geral.columns[13]
            df_cargos = df_os_geral.groupby(nome_coluna_cargo).size().reset_index(name='Qtd OS')
            df_cargos = df_cargos.sort_values(by='Qtd OS', ascending=False)
            
            c1, c2 = st.columns([1, 2])
            with c1:
                st.dataframe(df_cargos, use_container_width=True, hide_index=True)
            with c2:
                fig_cargo = px.bar(
                    df_cargos, 
                    x='Qtd OS', 
                    y=nome_coluna_cargo, 
                    orientation='h', 
                    title="Volume por Cargo", 
                    text='Qtd OS'
                )
                fig_cargo.update_layout(yaxis={'categoryorder':'total ascending'}, height=450)
                st.plotly_chart(fig_cargo, use_container_width=True)
                
        except IndexError:
            st.error("A planilha de OS não possui colunas suficientes para encontrar a coluna N (índice 13).")


# TELA 2: EXIBIÇÃO DOS GRÁFICOS DO GP/CLIENTES SELECIONADOS
elif st.session_state.tela == 'graficos':
    gp_selecionado = st.session_state.gp_atual
    clientes_selecionados = st.session_state.cliente_atual

    texto_dashboard = clientes_selecionados[0] if len(clientes_selecionados) == 1 else f"Filtro Combinado ({len(clientes_selecionados)} Clientes)"
    st.subheader(f"Dashboard: {gp_selecionado} ➔ {texto_dashboard}")

    # Seleção de Visão Dinâmica (Gráficos Volumétricos vs Roadmap Gantt Fixo)
    st.write("")
    visao_selecionada = st.radio(
        "Selecione a Visão desejada:",
        ["Volumetria e Gráficos", "Roadmap Geral (Milestones em Gantt)"],
        horizontal=True
    )
    st.write("---")

    try:
        col_status = 'status' if 'status' in df_os_geral.columns else df_os_geral.columns[7]
        nome_coluna_usuario = df_os_geral.columns[12]
        
        primeiro_nome_gp = gp_selecionado.split('_')[0].strip().lower()
        
        df_os_usuario_gp_geral = df_os_geral[
            df_os_geral[nome_coluna_usuario].astype(str).str.lower().str.contains(primeiro_nome_gp, na=False)
        ]
        qtd_os_usuario_geral = len(df_os_usuario_gp_geral)

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

        df_os_filtrado_gp = df_os_geral[df_os_geral[col_cliente].apply(cliente_pertence_ao_gp)]

        mascaras = []
        for cli in clientes_selecionados:
            nome_sel_limpo = str(cli).strip().lower()
            mascaras.append(
                df_os_filtrado_gp[col_cliente].astype(str).str.strip().str.lower().str.contains(nome_sel_limpo) |
                df_os_filtrado_gp[col_cliente].astype(str).str.strip().str.lower().apply(lambda x: x in nome_sel_limpo)
            )
        df_os_final = df_os_filtrado_gp[pd.concat(mascaras, axis=1).any(axis=1)]

        if len(df_os_final) > 0:
            df_os_usuario_gp_filtrado = df_os_final[
                df_os_final[nome_coluna_usuario].astype(str).str.lower().str.contains(primeiro_nome_gp, na=False)
            ]
            qtd_os_usuario_filtrado = len(df_os_usuario_gp_filtrado)
        else:
            qtd_os_usuario_filtrado = 0

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(label="Clientes Selecionados", value=len(clientes_selecionados))
        with col2:
            st.metric(label="Total de OS dos Clientes", value=len(df_os_final), 
                      help="Quantidade total de OS que pertencem a estes clientes no sistema.")
        with col3:
            st.metric(label=f"OS com {gp_selecionado} (Destes Clientes)", value=qtd_os_usuario_filtrado,
                      help="Quantidade de OS dos clientes selecionados que estão de fato atribuídas a este usuário (busca por primeiro nome).")
        with col4:
            st.metric(label=f"OS com {gp_selecionado} (Total Geral)", value=qtd_os_usuario_geral,
                      help="Volume total de OS deste usuário em toda a planilha, independente do cliente (busca por primeiro nome).")

        st.write("---")

        # ==========================================================
        # CONDIÇÃO 1: EXIBIÇÃO ORIGINAL DE VOLUMETRIA
        # ==========================================================
        if visao_selecionada == "Volumetria e Gráficos":
            if len(df_os_final) > 0:
                df_volumetria = df_os_final.groupby(col_cliente).size().reset_index(name='Quantidade')
                df_volumetria = df_volumetria.sort_values(by='Quantidade', ascending=False)
                
                graf1, graf2 = st.columns(2)

                with graf1:
                    df_top20 = df_volumetria.head(20)
                    fig_pizza_top = px.pie(df_top20, values='Quantidade', names=col_cliente, title="Distribuição de volume de OS por cliente")
                    fig_pizza_top.update_traces(textinfo='percent+value', textposition='inside')
                    st.plotly_chart(fig_pizza_top, use_container_width=True)
                    
                    st.write("---")
                    
                    df_barras_completo = df_volumetria.sort_values(by='Quantidade', ascending=True)
                    fig_barras_clientes = px.bar(df_barras_completo, x='Quantidade', y=col_cliente, orientation='h', title="Quantidade total de OS por cliente", text='Quantidade')
                    altura_dinamica = max(400, len(df_barras_completo) * 25)
                    fig_barras_clientes.update_layout(height=altura_dinamica, yaxis={'type': 'category'})
                    fig_barras_clientes.update_traces(textposition='outside')
                    st.plotly_chart(fig_barras_clientes, use_container_width=True)

                with graf2:
                    df_barras = df_os_final.groupby([col_status]).size().reset_index(name='Quantidade')
                    fig_barras = px.bar(df_barras, x=col_status, y='Quantidade', title="Quantidade de OS por Status", color=col_status, text='Quantidade')
                    fig_barras.update_traces(textposition='outside')
                    st.plotly_chart(fig_barras, use_container_width=True)
                              
            else:
                st.info("Nenhuma Ordem de Serviço encontrada para as condições selecionadas.")

        # ==========================================================
        # CONDIÇÃO 2: ROADMAP CONCEITUAL EM GRAFICO DE GANTT (SEM OSs)
        # ==========================================================
        else:
            st.subheader("Linha do Tempo Macro do Projeto")
            
            # 1. Definição estrita das 11 fases do fluxo
            ordem_milestones = [
                "Oportunidade", "Viabilidade", "Venda", "Fila ESC", 
                "Engenharia", "Validação GP", "Configuração", 
                "Validação GP 2", "Termo de Entrega", "Fecha OS", "Plano"
            ]
            
            # 2. Geração de datas sequenciais mockadas apenas para desenhar as barras do Gantt
            cronograma_fixo = []
            data_inicio = pd.to_datetime("2026-01-01")
            
            for i, etapa in enumerate(ordem_milestones):
                inicio_etapa = data_inicio + pd.Timedelta(days=i * 5)
                fim_etapa = inicio_etapa + pd.Timedelta(days=5)
                
                cronograma_fixo.append({
                    "Milestone": etapa,
                    "Início": inicio_etapa,
                    "Término": fim_etapa
                })
                
            df_gantt = pd.DataFrame(cronograma_fixo)
            
            # 3. Construção do Gráfico de Gantt
            fig_gantt = px.timeline(
                df_gantt, 
                x_start="Início", 
                x_end="Término", 
                y="Milestone", 
                color="Milestone",
                title="Estrutura de Sequenciamento dos Milestones Oficiais",
                labels={"Milestone": "Etapa do Fluxo"}
            )
            
            # Inverte o eixo Y para o fluxo começar por 'Oportunidade' no topo e limpa legendas redundantes
            fig_gantt.update_layout(
                yaxis={'categoryorder': 'array', 'categoryarray': ordem_milestones[::-1]},
                showlegend=False,
                height=500
            )
            
            # Limpa as labels de calendário do Eixo X para manter o foco unicamente conceitual do fluxo linear
            fig_gantt.update_xaxes(showticklabels=False, title="Fluxo Contínuo de Entrega")
            
            st.plotly_chart(fig_gantt, use_container_width=True)

    except Exception as e:
        st.error(f"Erro ao processar os gráficos filtrados: {e}")
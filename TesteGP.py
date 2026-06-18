import streamlit as st
import pandas as pd

# Configuração da página
st.set_page_config(page_title="Dashboard Google Sheets", layout="wide")

st.title("Gestão de GPs e Clientes (Google Sheets)")
st.markdown("Conectado em tempo real com a sua Google Planilha.")
st.write("---")

# 1. Cole aqui o ID da sua planilha (fica entre '/d/' e '/edit' no link que você copiou)
ID_PLANILHA = '1jQkoDfW438MtuGaTsoBrO_sNk-oj2Zwp0UXeBohJeCg'

# 2. Como cada GP está numa aba, precisamos listar os nomes dos GPs.
# IMPORTANTE: Para o código saber o nome das abas do Google Sheets de forma dinâmica,
# nós usamos um pequeno truque de leitura de tabelas do Google:
url_abas = f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA}/pubhtml"

@st.cache_data(ttl=60) # Atualiza o cache a cada 60 segundos
def buscar_nomes_abas(url):
    # Lê as tabelas da página pública para extrair os nomes dos GPs (abas)
    html_sheets = pd.read_html(url)
    # O pandas lê cada aba como uma tabela, mas precisamos configurar uma conexão direta para os dados reais
    return html_sheets

# Para simplificar e não precisar de senhas/credenciais complexas do Google Cloud,
# o jeito mais prático é você listar os nomes dos seus GPs manualmente em uma lista aqui no código,
# OU colocar o nome exato das abas nesta lista abaixo:
lista_gps = ["Fausto", "MauricioOrtiga", "MauricioFavero", "Cristiane", "Cristiane", "Nasare", "Jhonanthan"] 

# Se você preferir que o Python descubra as abas sozinho sem você digitar,
# o ideal é usar a API oficial do Google (com arquivo de chave .json).
# Para este teste rápido, digite o nome de 2 ou 3 abas suas na lista_gps acima.

# 3. Barra Lateral para Filtros
st.sidebar.header("Filtros")
gp_selecionado = st.sidebar.selectbox("Selecione o Gerente de Projeto (GP):", lista_gps)

# 4. Função para puxar os dados da aba selecionada em tempo real
@st.cache_data(ttl=10) # Se alguém atualizar a planilha, o Streamlit espera no máximo 10 segundos para puxar o dado novo
def carregar_dados_gp(id_planilha, nome_aba):
    # Formata a URL para exportar uma aba específica como CSV
    url_csv = f"https://docs.google.com/spreadsheets/d/{id_planilha}/gviz/tq?tqx=out:csv&sheet={nome_aba}"
    return pd.read_csv(url_csv)

try:
    # Carrega os dados da aba do Google Sheets
    df_clientes = carregar_dados_gp(ID_PLANILHA, gp_selecionado)

    # 5. Exibição no Dashboard
    st.subheader(f"Carteira de Clientes: {gp_selecionado}")
    
    total_clientes = len(df_clientes)
    st.metric(label="Total de Clientes Atendidos", value=total_clientes)
    
    st.write("### Listagem Detalhada")
    st.dataframe(df_clientes, use_container_width=True)

except Exception as e:
    st.error(f"Erro ao conectar com o Google Sheets: {e}")
    st.info("Verifique se o ID da planilha está correto e se ela está configurada como 'Qualquer pessoa com o link'.")
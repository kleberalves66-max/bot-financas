import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import google.generativeai as genai

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(
    page_title="Meu Financeiro AI",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo Dark Mode personalizado
st.markdown("""
    <style>
    .main { background-color: #0f172a; color: #f8fafc; }
    .stMetric { background-color: #1e293b; padding: 15px; border-radius: 10px; border: 1px solid #334155; }
    div[data-testid="stMetricValue"] { color: #22c55e !important; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# 2. CONFIGURAÇÕES DAS CHAVES (Chave limpa, sem espaços em branco)
SUPABASE_URL = "https://gnmendbdydjbdrsqqkna.supabase.co"
SUPABASE_KEY = "sb_publishable_gPogwuved8rqIcq9WJQGw_mcaaEVuB"
GEMINI_API_KEY = "AQ.Ab8RN6J5ARZnTPrdG-eOYLLm68kBILQT4ktqMeUS_n3mF3qp1g"

# Removemos o cache da conexão para forçar a validação real da chave limpa
def init_connections():
    supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    genai.configure(api_key=GEMINI_API_KEY)
    return supabase_client

try:
    supabase = init_connections()
except Exception as e:
    st.error(f"Erro ao conectar às APIs: {e}")
    st.stop()

# 3. BUSCA DE DADOS DO SUPABASE
def carregar_dados():
    try:
        # Busca os dados em tempo real sem travar no cache antigo
        response = supabase.table("transacoes").select("*").order("data", desc=True).execute()
        df = pd.DataFrame(response.data)
        if not df.empty:
            df['data'] = pd.to_datetime(df['data'])
            df['valor'] = pd.to_numeric(df['valor'])
        return df
    except Exception as e:
        st.error(f"⚠️ Erro ao aceder ao Supabase: {e}")
        return pd.DataFrame()

df_original = carregar_dados()

# TRAVA DE SEGURANÇA: Se o banco vier vazio ou der erro de validação
if df_original.empty:
    st.warning("📢 O aplicativo está no ar, mas não conseguiu ler nenhuma informação.")
    st.markdown("""
    ### 💡 Como resolver isso no seu painel do Supabase:
    1. **Verifique o nome da tabela:** Confirme se o nome dela é exatamente `transacoes` (tudo minúsculo e sem acento). Se mudou o nome lá, ajuste na linha 42 deste código.
    2. **Desative o RLS:** No painel do Supabase, entre na sua tabela, clique no botão **RLS Enabled** (no canto superior direito) e mude para **Disable RLS**.
    """)
    st.stop()

# 4. BARRA LATERAL (FILTROS DINÂMICOS)
st.sidebar.header("🎯 Filtros do Dashboard")

df_original['ano_mes'] = df_original['data'].dt.to_period('M')
lista_meses = sorted(df_original['ano_mes'].unique().astype(str), reverse=True)

mes_selecionado = st.sidebar.selectbox("Selecione o Mês de Análise", lista_meses)
df_filtrado = df_original[df_original['ano_mes'].astype(str) == mes_selecionado].copy()

# 5. CÁLCULO DE MÉTRICAS (KPIs)
receitas = df_filtrado[df_filtrado['tipo'].str.lower() == 'entrada']['valor'].sum()
despesas = df_filtrado[df_filtrado['tipo'].str.lower() == 'saida']['valor'].sum()
saldo_atual = receitas - despesas

st.title("💰 Meu Financeiro AI — Dashboard")
st.subheader(f"Análise Mensal de Referência: {mes_selecionado}")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Saldo Consolidado", value=f"R$ {saldo_atual:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
with col2:
    st.metric(label="Total de Receitas (🟢)", value=f"R$ {receitas:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
with col3:
    st.metric(label="Total de Despesas (🔴)", value=f"R$ {despesas:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

st.markdown("---")

# 6. ÁREA DE GRÁFICOS
col_graf1, col_graf2 = st.columns([1, 1])

with col_graf1:
    st.subheader("📊 Distribuição de Gastos por Categoria")
    df_gastos = df_filtrado[df_filtrado['tipo'].str.lower() == 'saida']
    
    if not df_gastos.empty:
        df_cat = df_gastos.groupby('categoria')['valor'].sum().reset_index()
        fig_rosca = px.pie(
            df_cat, 
            values='valor', 
            names='categoria', 
            hole=0.5,
            template="plotly_dark",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_rosca.update_layout(margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_rosca, use_container_width=True)
    else:
        st.info("Nenhuma despesa registrada neste mês.")

with col_graf2:
    st.subheader("📅 Histórico de Transações do Mês")
    df_exibicao = df_filtrado[['data', 'descricao', 'categoria', 'tipo', 'valor']].copy()
    df_exibicao['data'] = df_exibicao['data'].dt.strftime('%d/%m/%Y')
    st.dataframe(df_exibicao, use_container_width=True, hide_index=True)

st.markdown("---")

# 7. INTELIGÊNCIA ARTIFICIAL (GEMINI INSIGHTS)
st.subheader("🧠 Consultoria de Inteligência Artificial — Gemini")

if st.button("✨ Gerar Novos Insights com IA"):
    dados_para_ia = df_filtrado[['descricao', 'categoria', 'tipo', 'valor']].to_string(index=False)

    prompt_contexto = f"""
    Você é um consultor financeiro pessoal inteligente, focado e muito prático.
    Analise os dados reais de gastos do usuário Kleber para o mês {mes_selecionado}:
    Saldo Atual: R$ {saldo_atual:.2f}
    Total de Receitas: R$ {receitas:.2f}
    Total de Despesas: R$ {despesas:.2f}

    Transações detalhadas do período:
    {dados_para_ia}

    Gere um insight curto, direto ao ponto, no estilo de uma mensagem de WhatsApp, chamando o Kleber pelo nome. 
    Diga qual é o saldo atual dele, elogie se ele estiver economizando ou dê um alerta claro e amigável sobre qual categoria ou gasto específico consumiu a maior parte do dinheiro dele neste mês, sugerindo uma ação simples para organizar.
    Use emojis apropriados.
    """

    with st.spinner("O Gemini está analisando os dados..."):
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt_contexto)
            st.info(response.text)
        except Exception as e:
            st.error(f"Não foi possível carregar o insight da IA: {e}")
else:
    st.caption("Clique no botão acima para ativar a inteligência artificial.")
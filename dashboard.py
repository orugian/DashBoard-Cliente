import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Dashboard Financeiro - Cemil Tubos",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILIZAÇÃO (CSS) ---
st.markdown("""
<style>
    /* Estilo para o Grande Número do Saldo Atual */
    .big-metric {
        font-size: 42px !important;
        font-weight: 800;
        color: #C0392B; /* Vermelho sangue para atenção */
    }
    .metric-label {
        font-size: 18px;
        color: #555;
        font-weight: 600;
    }
    .metric-container {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #C0392B;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
        text-align: center;
    }
    [data-testid="stMetricValue"] {
        font-size: 26px;
        color: #2E86C1;
    }
    div.stButton > button {
        background-color: #2E86C1;
        color: white;
        border-radius: 8px;
    }
    .big-font {
        font-size: 16px !important;
        color: #555;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÃO DE CARREGAMENTO DE DADOS ---


@st.cache_data
def load_data():
    file_excel = "dados_financeiros.xlsx"

    # 1. ABA RESUMO
    df_resumo = pd.read_excel(
        file_excel, sheet_name="Resumo", header=None, skiprows=2)
    df_resumo[0] = df_resumo[0].astype(str).str.strip()
    resumo_dict = dict(zip(df_resumo.iloc[:, 0], df_resumo.iloc[:, 1]))

    # 2. ABA PARÂMETROS
    df_params_raw = pd.read_excel(
        file_excel, sheet_name="Parâmetros", header=None, skiprows=2)
    df_selic = df_params_raw.iloc[4:].reset_index(drop=True)
    df_selic.columns = ['Competência', 'Taxa Mensal (%)']
    df_selic = df_selic.dropna(subset=['Competência'])
    df_selic['Taxa Mensal (%)'] = pd.to_numeric(
        df_selic['Taxa Mensal (%)'], errors='coerce')

    # 3. ABA MODELO B
    df_modelo = pd.read_excel(file_excel, sheet_name="Modelo B", skiprows=4)
    df_modelo['Data prevista'] = pd.to_datetime(
        df_modelo['Data prevista'], errors='coerce')
    df_modelo['Data pagamento'] = pd.to_datetime(
        df_modelo['Data pagamento'], errors='coerce')

    # Lógica de Status
    df_modelo['Status'] = df_modelo['Valor pago'].apply(
        lambda x: '✅ Pago' if pd.notnull(x) and x > 0 else '⏳ Pendente'
    )

    return resumo_dict, df_selic, df_modelo


# --- CARREGAMENTO ---
try:
    resumo, df_selic, df_modelo = load_data()
except FileNotFoundError:
    st.error("⚠️ Arquivo 'dados_financeiros.xlsx' não encontrado.")
    st.stop()

# --- SIDEBAR ---
st.sidebar.title("🎛️ Controles")
status_filter = st.sidebar.multiselect(
    "Filtrar por Status:", options=df_modelo['Status'].unique(), default=df_modelo['Status'].unique())
df_filtered = df_modelo[df_modelo['Status'].isin(status_filter)]

# --- FUNÇÃO AUXILIAR PARA VALORES ---


def get_val(key_part):
    for k, v in resumo.items():
        if key_part.lower() in str(k).lower():
            try:
                return float(v)
            except:
                return 0.0
    return 0.0


# --- CÁLCULOS PRINCIPAIS ---
saldo_inicial_orig = get_val("Saldo inicial (original)")
abatimento_tecnomonte = abs(get_val("Abatimento Tecnomonte"))
total_pago_hist = abs(get_val("Total pago"))

# LÓGICA DO SALDO ATUAL REAL (Dinâmico do Modelo B)
# Procura a última parcela paga e pega o saldo remanescente dela
df_pagos = df_modelo[df_modelo['Status'] == '✅ Pago']

if not df_pagos.empty:
    ultimo_pagamento = df_pagos.iloc[-1]
    saldo_devedor_atual = ultimo_pagamento['Saldo após pagamento']
    data_ultimo_pag = ultimo_pagamento['Data pagamento']
    texto_referencia = f"Posição atualizada após pagamento de {data_ultimo_pag.strftime('%d/%m/%Y')}"
    # Se houver pagamentos novos além do histórico do resumo, precisamos ajustar o total pago visualizado
    total_pago_real = saldo_inicial_orig - \
        abatimento_tecnomonte - saldo_devedor_atual
else:
    # Se nada foi pago no Modelo B, usa o saldo do resumo
    saldo_devedor_atual = saldo_inicial_orig - \
        abatimento_tecnomonte - total_pago_hist
    total_pago_real = total_pago_hist
    texto_referencia = "Posição baseada no Saldo Inicial (Nenhum pagamento registrado no cronograma)"

# --- DASHBOARD ---
st.title("📊 Painel de Controle Financeiro - Cemil Tubos")
st.markdown(
    f"**Data Base do Relatório:** {datetime.now().strftime('%d/%m/%Y')}")
st.divider()

# --- SEÇÃO DESTAQUE: O NÚMERO QUE IMPORTA ---
st.markdown("### 🚨 Posição Atual da Dívida")
col_destaque, col_vazia = st.columns([1, 2])

with col_destaque:
    st.markdown(f"""
    <div class='metric-container'>
        <div class='metric-label'>SALDO DEVEDOR EM ABERTO</div>
        <div class='big-metric'>R$ {saldo_devedor_atual:,.2f}</div>
        <div style='font-size: 12px; color: #777; margin-top: 5px;'>{texto_referencia}</div>
    </div>
    """, unsafe_allow_html=True)

with col_vazia:
    st.info("""
    **O que este valor representa?**
    
    Este é o montante exato que a **Cemil Tubos** ainda deve, já descontando:
    1. O abatimento inicial da Tecnomonte.
    2. Todos os pagamentos históricos.
    3. A última parcela quitada registrada no cronograma.
    """)

st.divider()

# --- MEMÓRIA DE CÁLCULO (WATERFALL) ---
st.subheader("💡 Composição Histórica do Saldo")
col_meta, col_graf = st.columns([1, 2])

with col_meta:
    st.markdown(f"""
    <div class='big-font'>
    <b>Entenda a evolução:</b><br><br>
    Começamos com <b>R$ {saldo_inicial_orig:,.2f}</b>.<br>
    ➖ Abatemos <b>R$ {abatimento_tecnomonte:,.2f}</b> (Tecnomonte).<br>
    ➖ Recebemos <b>R$ {total_pago_real:,.2f}</b> em pagamentos totais.<br>
    <hr>
    <b>Restam: R$ {saldo_devedor_atual:,.2f}</b>
    </div>
    """, unsafe_allow_html=True)

with col_graf:
    fig_waterfall = go.Figure(go.Waterfall(
        name="Fluxo", orientation="v",
        measure=["absolute", "relative", "relative", "total"],
        x=["Dívida Original", "Abatimento Tecnomonte",
            "Total Pago", "Saldo Devedor Atual"],
        textposition="outside",
        text=[
            f"R$ {saldo_inicial_orig/1000:.0f}k",
            f"-{abatimento_tecnomonte/1000:.0f}k",
            f"-{total_pago_real/1000:.0f}k",
            f"{saldo_devedor_atual/1000:.0f}k"
        ],
        y=[saldo_inicial_orig, -abatimento_tecnomonte, -
            total_pago_real, saldo_devedor_atual],
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        # Verde para o que abate a dívida
        decreasing={"marker": {"color": "#2ECC71"}},
        # Vermelho (se houvesse aumento)
        increasing={"marker": {"color": "#E74C3C"}},
        # Vermelho escuro para o saldo a pagar
        totals={"marker": {"color": "#C0392B"}}
    ))
    fig_waterfall.update_layout(
        title="Gráfico de Abatimentos",
        showlegend=False,
        template="plotly_white",
        height=350,
        margin=dict(l=0, r=0, t=40, b=0)
    )
    st.plotly_chart(fig_waterfall, use_container_width=True)

st.divider()

# --- KPI GERAIS E GRÁFICOS ---
c1, c2, c3 = st.columns(3)
parcelas_pendentes = df_modelo[df_modelo['Status'] == '⏳ Pendente'].shape[0]

c1.metric("💰 Valor Original", f"R$ {saldo_inicial_orig:,.2f}")
c2.metric("📅 Parcelas Restantes", f"{parcelas_pendentes} Semanas")
c3.metric("📉 Percentual Quitado",
          f"{(total_pago_real + abatimento_tecnomonte)/saldo_inicial_orig*100:.1f}%")

tab1, tab2, tab3 = st.tabs(
    ["📈 Projeção Futura", "📋 Extrato Completo", "🏦 Taxas SELIC"])

with tab1:
    fig_line = px.line(
        df_filtered, x='Data prevista', y='Saldo após pagamento', markers=True,
        title='Curva de Amortização da Dívida',
        labels={
            'Saldo após pagamento': 'Saldo Devedor (R$)', 'Data prevista': 'Vencimento'}
    )
    # Vermelho para dívida
    fig_line.update_traces(line_color='#C0392B', line_width=3)
    st.plotly_chart(fig_line, use_container_width=True)

with tab2:
    st.dataframe(
        df_filtered[['Parcela #', 'Data prevista',
                     'Valor parcela', 'Status', 'Saldo após pagamento']],
        column_config={
            "Valor parcela": st.column_config.NumberColumn(format="R$ %.2f"),
            "Saldo após pagamento": st.column_config.NumberColumn(format="R$ %.2f"),
            "Data prevista": st.column_config.DateColumn(format="DD/MM/YYYY"),
        },
        use_container_width=True,
        hide_index=True,
        height=400
    )

with tab3:
    if not df_selic.empty:
        fig_selic = px.bar(df_selic, x='Competência', y='Taxa Mensal (%)',
                           text_auto='.4f', title='Índices SELIC Aplicados')
        st.plotly_chart(fig_selic, use_container_width=True)
    else:
        st.info("Nenhuma taxa SELIC carregada.")

st.markdown("---")
st.caption("🔒 Documento Confidencial | Gerado via ENI Systems.")

import streamlit as st
import pandas as pd
import plotly.express as px

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="Dashboard de Vendas",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# GESTÃO DE DADOS E REGISTOS MANUAIS
# ==============================================================================
if 'vendas_manuais' not in st.session_state:
    st.session_state['vendas_manuais'] = []

@st.cache_data
def carregar_dados_base():
    df = pd.read_csv('vendas.csv')
    df['data'] = pd.to_datetime(df['data'])
    return df

# Carrega a base original e concatena com registos manuais adicionados nesta sessão
df_base = carregar_dados_base()

if st.session_state['vendas_manuais']:
    df_manuais = pd.DataFrame(st.session_state['vendas_manuais'])
    df_manuais['data'] = pd.to_datetime(df_manuais['data'])
    df = pd.concat([df_base, df_manuais], ignore_index=True)
else:
    df = df_base.copy()

# ==============================================================================
# FUNÇÃO DE FORMATAÇÃO MONETÁRIA EM MZN
# ==============================================================================
def formatar_mzn(valor):
    if pd.isna(valor) or valor == 0:
        return "0,00 MZN"
    return f"{valor:,.2f}".replace(",", " ").replace(".", ",") + " MZN"

# ==============================================================================
# BARRA LATERAL (FILTROS)
# ==============================================================================
st.sidebar.header("🔍 Filtros de Vendas")

# 1. Filtro de Cidade
todas_cidades = sorted(df['cidade'].unique().tolist())
cidades_selecionadas = st.sidebar.multiselect(
    "Cidade:",
    options=todas_cidades,
    default=todas_cidades,
    placeholder="Selecione uma ou mais cidades"
)

# 2. Filtro de Produto
todos_produtos = sorted(df['produto'].unique().tolist())
produtos_selecionados = st.sidebar.multiselect(
    "Produto:",
    options=todos_produtos,
    default=todos_produtos,
    placeholder="Selecione um ou mais produtos"
)

# 3. Filtro de Período / Data
data_minima = df['data'].min().date()
data_maxima = df['data'].max().date()

intervalo_datas = st.sidebar.date_input(
    "Período:",
    value=(data_minima, data_maxima),
    min_value=data_minima,
    max_value=data_maxima
)

# Validação do intervalo de datas
if isinstance(intervalo_datas, (tuple, list)) and len(intervalo_datas) == 2:
    data_inicio, data_fim = intervalo_datas
else:
    data_inicio, data_fim = data_minima, data_maxima

# Filtragem do DataFrame
df_filtrado = df[
    (df['cidade'].isin(cidades_selecionadas)) &
    (df['produto'].isin(produtos_selecionados)) &
    (df['data'].dt.date >= data_inicio) &
    (df['data'].dt.date <= data_fim)
]

# Botão de exportação na barra lateral
st.sidebar.divider()
st.sidebar.download_button(
    label="📥 Descarregar Dados (CSV)",
    data=df_filtrado.to_csv(index=False).encode('utf-8'),
    file_name="vendas_filtrado.csv",
    mime="text/csv",
    use_container_width=True,
    help="Exportar os dados selecionados em formato CSV para partilhar com o cliente"
)

# ==============================================================================
# CABEÇALHO DA DASHBOARD
# ==============================================================================
st.title("📊 Dashboard de Vendas")
st.markdown("Acompanhamento de vendas, faturamento por região e volume de produtos.")
st.divider()

# ==============================================================================
# INSERÇÃO MANUAL DE NOVO PRODUTO / VENDA
# ==============================================================================
with st.expander("➕ Registar Novo Produto ou Venda Manualmente", expanded=False):
    st.markdown("Preencha o formulário abaixo para registar uma nova venda ou produto diretamente na Dashboard.")
    
    with st.form("form_registo_manual", clear_on_submit=True):
        col_m1, col_m2, col_m3 = st.columns(3)

        with col_m1:
            nova_data = st.date_input("Data da Transação:", value=pd.to_datetime("today").date())
            lista_cidades = sorted(df['cidade'].unique().tolist())
            cid_opcao = st.selectbox(
                "Cidade Existente:",
                ["-- Escolher Existente --"] + lista_cidades,
                help="Selecione uma cidade já registada na tabela"
            )
            cid_personalizada = st.text_input(
                "Ou digite uma NOVA Cidade:",
                placeholder="Ex: Beira, Nampula, Tete, Pemba...",
                help="Escreva aqui caso queira adicionar uma nova praça de vendas"
            )

        with col_m2:
            lista_produtos = sorted(df['produto'].unique().tolist())
            prod_opcao = st.selectbox(
                "Produto Existente:",
                ["-- Escolher Existente --"] + lista_produtos,
                help="Selecione um produto que já existe no catálogo"
            )
            prod_personalizado = st.text_input(
                "Ou digite um NOVO Produto:",
                placeholder="Ex: Smartphone, Projetor, Cadeira, Switch...",
                help="Escreva aqui qualquer produto diferente que ainda não conste na tabela"
            )

        with col_m3:
            qtd_manual = st.number_input("Quantidade:", min_value=1, value=1, step=1)
            preco_manual = st.number_input("Preço Unitário (MZN):", min_value=1, value=1000, step=100)

        # Cálculo automático da receita da nova transação
        total_previsto = int(qtd_manual * preco_manual)
        st.info(f"💵 **Valor Calculado da Venda:** {formatar_mzn(total_previsto)}")

        btn_confirmar = st.form_submit_button("💾 Adicionar Venda à Dashboard", use_container_width=True)

        if btn_confirmar:
            # Resolução do nome do produto e da cidade (com prioridade para o novo texto digitado)
            if prod_personalizado.strip():
                produto_final = prod_personalizado.strip().title()
            elif prod_opcao != "-- Escolher Existente --":
                produto_final = prod_opcao
            else:
                produto_final = ""

            if cid_personalizada.strip():
                cidade_final = cid_personalizada.strip().title()
            elif cid_opcao != "-- Escolher Existente --":
                cidade_final = cid_opcao
            else:
                cidade_final = ""

            if not cidade_final:
                st.error("⚠️ Por favor, escolha ou digite o nome de uma cidade.")
            elif not produto_final:
                st.error("⚠️ Por favor, escolha ou digite o nome de um produto.")
            else:
                novo_registo = {
                    'data': nova_data.strftime('%Y-%m-%d'),
                    'produto': produto_final,
                    'cidade': cidade_final,
                    'quantidade': int(qtd_manual),
                    'preco_unitario': int(preco_manual),
                    'valor_venda': total_previsto
                }

                # Atualiza os dados na sessão ativa da Dashboard
                st.session_state['vendas_manuais'].append(novo_registo)

                # Tenta persistir no vendas.csv físico
                try:
                    linha_csv = f"\n{novo_registo['data']},{novo_registo['produto']},{novo_registo['cidade']},{novo_registo['quantidade']},{novo_registo['preco_unitario']},{novo_registo['valor_venda']}"
                    with open('vendas.csv', 'a', encoding='utf-8') as f:
                        f.write(linha_csv)
                    st.cache_data.clear()
                    st.success(f"✅ Venda de **{produto_final}** guardada no vendas.csv e integrada na Dashboard!")
                except PermissionError:
                    st.success(f"✅ Venda de **{produto_final}** adicionada com sucesso à Dashboard! (Dica: Se o ficheiro vendas.csv estiver aberto no WPS/Excel, a gravação em disco fica pendente até fechar o programa).")

                st.rerun()

# ==============================================================================
# SEÇÃO 1: KPIS (FASE 4)
# ==============================================================================
if df_filtrado.empty:
    st.warning("⚠️ Nenhum registo encontrado com os filtros selecionados. Ajuste os filtros na barra lateral.")
else:
    # Cálculos dos KPIs com base nos dados filtrados
    faturamento_total = df_filtrado['valor_venda'].sum()
    total_vendas = len(df_filtrado)
    quantidade_total = df_filtrado['quantidade'].sum()
    ticket_medio = df_filtrado['valor_venda'].mean()

    # Exibição dos KPIs em 4 colunas no topo
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    with kpi1:
        st.metric(
            label="💰 Faturamento Total",
            value=formatar_mzn(faturamento_total)
        )

    with kpi2:
        st.metric(
            label="🧾 Total de Vendas",
            value=f"{total_vendas} vendas"
        )

    with kpi3:
        st.metric(
            label="📦 Quantidade Vendida",
            value=f"{quantidade_total} un"
        )

    with kpi4:
        st.metric(
            label="🎯 Ticket Médio",
            value=formatar_mzn(ticket_medio)
        )

    st.divider()

    # ==============================================================================
    # SEÇÃO 2: GRÁFICOS INTERATIVOS PLOTLY (FASE 5)
    # ==============================================================================
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        # Gráfico 1: Faturamento por Produto (Barras Verticais)
        fat_prod = (
            df_filtrado.groupby('produto')['valor_venda']
            .sum()
            .reset_index()
            .sort_values('valor_venda', ascending=False)
        )
        fig_fat_prod = px.bar(
            fat_prod,
            x='produto',
            y='valor_venda',
            title='<b>Faturamento por Produto</b>',
            labels={'produto': 'Produto', 'valor_venda': 'Faturamento (MZN)'},
            text_auto='.2s',
            color='produto'
        )
        fig_fat_prod.update_layout(showlegend=False, xaxis_title="", yaxis_title="MZN")
        st.plotly_chart(fig_fat_prod, use_container_width=True)

    with col_g2:
        # Gráfico 2: Faturamento por Cidade (Donut / Rosca)
        fat_cid = (
            df_filtrado.groupby('cidade')['valor_venda']
            .sum()
            .reset_index()
            .sort_values('valor_venda', ascending=False)
        )
        fig_fat_cid = px.pie(
            fat_cid,
            names='cidade',
            values='valor_venda',
            title='<b>Faturamento por Cidade</b>',
            hole=0.45
        )
        fig_fat_cid.update_traces(textinfo='percent+label')
        st.plotly_chart(fig_fat_cid, use_container_width=True)

    col_g3, col_g4 = st.columns(2)

    with col_g3:
        # Gráfico 3: Evolução Temporal (Linha com Marcadores)
        fat_tempo = (
            df_filtrado.groupby('data')['valor_venda']
            .sum()
            .reset_index()
            .sort_values('data')
        )
        fig_tempo = px.line(
            fat_tempo,
            x='data',
            y='valor_venda',
            title='<b>Evolução do Faturamento ao Longo do Tempo</b>',
            labels={'data': 'Data', 'valor_venda': 'Faturamento (MZN)'},
            markers=True
        )
        fig_tempo.update_layout(xaxis_title="", yaxis_title="MZN")
        st.plotly_chart(fig_tempo, use_container_width=True)

    with col_g4:
        # Gráfico 4: Quantidade Vendida por Produto (Barras Horizontais)
        qtd_prod = (
            df_filtrado.groupby('produto')['quantidade']
            .sum()
            .reset_index()
            .sort_values('quantidade', ascending=True)
        )
        fig_qtd_prod = px.bar(
            qtd_prod,
            x='quantidade',
            y='produto',
            orientation='h',
            title='<b>Quantidade Vendida por Produto</b>',
            labels={'quantidade': 'Unidades', 'produto': 'Produto'},
            text_auto=True,
            color='quantidade'
        )
        fig_qtd_prod.update_layout(coloraxis_showscale=False, yaxis_title="", xaxis_title="Unidades")
        st.plotly_chart(fig_qtd_prod, use_container_width=True)

    st.divider()

    # ==============================================================================
    # SEÇÃO 3: TABELA COM OS DADOS FILTRADOS E EXPORTAÇÃO CSV
    # ==============================================================================
    col_tab_tit, col_tab_btn = st.columns([3, 1])
    with col_tab_tit:
        st.subheader("📋 Tabela de Registos de Vendas")
        st.markdown("Visualização detalhada das transações correspondentes aos filtros aplicados.")
    with col_tab_btn:
        # Conversão do DataFrame filtrado para CSV codificado em UTF-8
        csv_bytes = df_filtrado.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descarregar CSV",
            data=csv_bytes,
            file_name="relatorio_vendas.csv",
            mime="text/csv",
            use_container_width=True,
            help="Descarregar os dados filtrados em formato CSV para partilhar com o cliente"
        )

    # Criação de uma cópia para apresentação com formatação amigável
    df_tabela = df_filtrado.copy()
    df_tabela['data'] = df_tabela['data'].dt.strftime('%Y-%m-%d')
    df_tabela['preco_unitario'] = df_tabela['preco_unitario'].apply(formatar_mzn)
    df_tabela['valor_venda'] = df_tabela['valor_venda'].apply(formatar_mzn)

    # Renomear as colunas para títulos legíveis
    df_tabela = df_tabela.rename(columns={
        'data': 'Data',
        'produto': 'Produto',
        'cidade': 'Cidade',
        'quantidade': 'Quantidade',
        'preco_unitario': 'Preço Unitário (MZN)',
        'valor_venda': 'Valor da Venda (MZN)'
    })

    st.dataframe(df_tabela, use_container_width=True, hide_index=True)

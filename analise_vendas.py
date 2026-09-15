"""
Script de Análise de Dados de Vendas (Fases 1 a 4)
Executa o diagnóstico, preparação e cálculo dos KPIs no terminal.
"""

import pandas as pd

def formatar_mzn(valor):
    if pd.isna(valor) or valor == 0:
        return "0,00 MZN"
    return f"{valor:,.2f}".replace(",", " ").replace(".", ",") + " MZN"

def main():
    print("=" * 60)
    print("        RELATÓRIO DE ANÁLISE DE DADOS - VENDAS.CSV")
    print("=" * 60)

    # 1. Carregamento dos dados
    df = pd.read_csv('vendas.csv')

    # FASE 1: Diagnóstico Inicial
    print("\n--- [FASE 1] DIAGNÓSTICO DOS DADOS ---")
    linhas, colunas = df.shape
    print(f"• Total de Registos (Linhas): {linhas}")
    print(f"• Total de Colunas: {colunas}")
    print(f"• Nomes das Colunas: {', '.join(df.columns.tolist())}")
    print(f"• Valores Vazios/Nulos: {df.isnull().sum().sum()} encontrados")
    print(f"• Linhas Duplicadas: {df.duplicated().sum()} encontradas")

    # FASE 2: Preparação
    print("\n--- [FASE 2] PREPARAÇÃO E LIMPEZA ---")
    df['data'] = pd.to_datetime(df['data'])
    df['mes'] = df['data'].dt.month
    print("• Coluna 'data' convertida com sucesso para datetime.")
    print("• Coluna 'mes' criada para agregações temporais.")

    # FASE 3 & 4: KPIs e Indicadores de Negócio
    print("\n--- [FASE 3 & 4] PRINCIPAIS KPIS E RESULTADOS ---")
    faturamento_total = df['valor_venda'].sum()
    total_vendas = len(df)
    quantidade_total = df['quantidade'].sum()
    ticket_medio = df['valor_venda'].mean()

    print(f"1. Faturamento Total:          {formatar_mzn(faturamento_total)}")
    print(f"2. Total de Transações:        {total_vendas} vendas")
    print(f"3. Quantidade Total Vendida:   {quantidade_total} unidades")
    print(f"4. Ticket Médio por Venda:     {formatar_mzn(ticket_medio)}")
    print(f"5. Preço Médio por Item:       {formatar_mzn(faturamento_total / quantidade_total)}")

    print("\n--- RANKING DE PRODUTOS POR FATURAMENTO ---")
    fat_prod = df.groupby('produto')['valor_venda'].sum().sort_values(ascending=False)
    for prod, val in fat_prod.items():
        print(f"  - {prod:<12}: {formatar_mzn(val)}")

    print("\n--- RANKING DE PRODUTOS POR VOLUME (UNIDADES) ---")
    qtd_prod = df.groupby('produto')['quantidade'].sum().sort_values(ascending=False)
    for prod, qtd in qtd_prod.items():
        print(f"  - {prod:<12}: {qtd:>3} unidades")

    print("\n--- FATURAMENTO POR PRAÇA (CIDADE) ---")
    fat_cid = df.groupby('cidade')['valor_venda'].sum().sort_values(ascending=False)
    for cid, val in fat_cid.items():
        perc = (val / faturamento_total) * 100
        print(f"  - {cid:<10}: {formatar_mzn(val)} ({perc:.1f}%)")

    print("\n" + "=" * 60)
    print("Análise concluída com sucesso!")
    print("Para abrir o painel gráfico interativo, execute: streamlit run app.py")
    print("=" * 60)

if __name__ == "__main__":
    main()

"""
API REST de Vendas em FastAPI para deploy no Render.
Processamento de dados com Pandas, cálculo de KPIs e persistência em CSV.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from pathlib import Path
import pandas as pd
import os

app = FastAPI(
    title="Dashboard de Vendas API",
    description="Backend para cálculo de KPIs e gestão de transações de vendas.",
    version="1.0.0"
)

# Habilitar CORS para permitir requisições de qualquer origem (Vercel, localhost, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "vendas.csv"
ROOT_CSV_PATH = BASE_DIR.parent / "vendas.csv"

def get_csv_file() -> Path:
    if CSV_PATH.exists():
        return CSV_PATH
    if ROOT_CSV_PATH.exists():
        return ROOT_CSV_PATH
    raise FileNotFoundError("O ficheiro vendas.csv não foi encontrado.")

def carregar_dados() -> pd.DataFrame:
    caminho = get_csv_file()
    df = pd.read_csv(caminho)
    df['data'] = pd.to_datetime(df['data'])
    return df

def filtrar_dataframe(
    df: pd.DataFrame,
    cidades: Optional[List[str]] = None,
    produtos: Optional[List[str]] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None
) -> pd.DataFrame:
    df_filtrado = df.copy()

    if cidades:
        df_filtrado = df_filtrado[df_filtrado['cidade'].isin(cidades)]

    if produtos:
        df_filtrado = df_filtrado[df_filtrado['produto'].isin(produtos)]

    if data_inicio:
        try:
            dt_ini = pd.to_datetime(data_inicio)
            df_filtrado = df_filtrado[df_filtrado['data'] >= dt_ini]
        except Exception:
            pass

    if data_fim:
        try:
            dt_fim = pd.to_datetime(data_fim)
            df_filtrado = df_filtrado[df_filtrado['data'] <= dt_fim]
        except Exception:
            pass

    return df_filtrado

class NovaVenda(BaseModel):
    data: str = Field(..., description="Data no formato YYYY-MM-DD")
    produto: str = Field(..., min_length=1)
    cidade: str = Field(..., min_length=1)
    quantidade: int = Field(..., gt=0)
    preco_unitario: float = Field(..., gt=0)
    valor_venda: Optional[float] = None

@app.get("/")
def home():
    return {
        "status": "online",
        "service": "Dashboard de Vendas API (Render)",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/api/filtros")
def obter_filtros():
    """Retorna listas únicas de cidades, produtos e limites de datas disponíveis."""
    try:
        df = carregar_dados()
        cidades = sorted(df['cidade'].dropna().unique().tolist())
        produtos = sorted(df['produto'].dropna().unique().tolist())
        data_min = df['data'].min().strftime('%Y-%m-%d') if not df.empty else ""
        data_max = df['data'].max().strftime('%Y-%m-%d') if not df.empty else ""

        return {
            "cidades": cidades,
            "produtos": produtos,
            "data_minima": data_min,
            "data_maxima": data_max
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/kpis")
def obter_kpis(
    cidade: Optional[List[str]] = Query(None),
    produto: Optional[List[str]] = Query(None),
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None
):
    """Calcula todos os indicadores de negócio e agregados para os gráficos."""
    try:
        df = carregar_dados()
        df_filtrado = filtrar_dataframe(df, cidade, produto, data_inicio, data_fim)

        if df_filtrado.empty:
            return {
                "faturamento_total": 0.0,
                "total_vendas": 0,
                "quantidade_total": 0,
                "ticket_medio": 0.0,
                "preco_medio_item": 0.0,
                "ranking_produtos_faturamento": [],
                "ranking_produtos_quantidade": [],
                "faturamento_por_cidade": [],
                "evolucao_temporal": []
            }

        faturamento_total = float(df_filtrado['valor_venda'].sum())
        total_vendas = int(len(df_filtrado))
        quantidade_total = int(df_filtrado['quantidade'].sum())
        ticket_medio = float(df_filtrado['valor_venda'].mean())
        preco_medio_item = float(faturamento_total / quantidade_total) if quantidade_total > 0 else 0.0

        # 1. Ranking de faturamento por produto
        fat_prod = (
            df_filtrado.groupby('produto')['valor_venda']
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )
        ranking_fat = [
            {"produto": row['produto'], "faturamento": float(row['valor_venda'])}
            for _, row in fat_prod.iterrows()
        ]

        # 2. Ranking de quantidade por produto
        qtd_prod = (
            df_filtrado.groupby('produto')['quantidade']
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )
        ranking_qtd = [
            {"produto": row['produto'], "quantidade": int(row['quantidade'])}
            for _, row in qtd_prod.iterrows()
        ]

        # 3. Faturamento por praça (cidade)
        fat_cid = (
            df_filtrado.groupby('cidade')['valor_venda']
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )
        dist_cidades = []
        for _, row in fat_cid.iterrows():
            f = float(row['valor_venda'])
            perc = (f / faturamento_total * 100.0) if faturamento_total > 0 else 0.0
            dist_cidades.append({
                "cidade": row['cidade'],
                "faturamento": f,
                "percentual": round(perc, 1)
            })

        # 4. Evolução temporal (ordenada por data)
        fat_tempo = (
            df_filtrado.groupby(df_filtrado['data'].dt.strftime('%Y-%m-%d'))['valor_venda']
            .sum()
            .reset_index()
            .rename(columns={'data': 'data_str'})
            .sort_values('data_str')
        )
        evolucao = [
            {"data": row['data_str'], "faturamento": float(row['valor_venda'])}
            for _, row in fat_tempo.iterrows()
        ]

        return {
            "faturamento_total": faturamento_total,
            "total_vendas": total_vendas,
            "quantidade_total": quantidade_total,
            "ticket_medio": ticket_medio,
            "preco_medio_item": preco_medio_item,
            "ranking_produtos_faturamento": ranking_fat,
            "ranking_produtos_quantidade": ranking_qtd,
            "faturamento_por_cidade": dist_cidades,
            "evolucao_temporal": evolucao
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/vendas")
def listar_vendas(
    cidade: Optional[List[str]] = Query(None),
    produto: Optional[List[str]] = Query(None),
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None
):
    """Lista as transações individuais filtradas."""
    try:
        df = carregar_dados()
        df_filtrado = filtrar_dataframe(df, cidade, produto, data_inicio, data_fim)
        df_filtrado = df_filtrado.sort_values('data', ascending=False)

        # Formatar a data para string legível
        df_saida = df_filtrado.copy()
        df_saida['data'] = df_saida['data'].dt.strftime('%Y-%m-%d')

        registos = df_saida.to_dict(orient="records")
        return {
            "total": len(registos),
            "vendas": registos
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/vendas", status_code=201)
def adicionar_venda(venda: NovaVenda):
    """Adiciona uma nova transação e persiste em vendas.csv."""
    try:
        # Calcular valor se não enviado
        valor_final = venda.valor_venda
        if valor_final is None or valor_final <= 0:
            valor_final = float(venda.quantidade * venda.preco_unitario)

        novo_registo = {
            'data': venda.data.strip(),
            'produto': venda.produto.strip().title(),
            'cidade': venda.cidade.strip().title(),
            'quantidade': int(venda.quantidade),
            'preco_unitario': float(venda.preco_unitario),
            'valor_venda': float(valor_final)
        }

        novo_df = pd.DataFrame([novo_registo])

        # Persistir no ficheiro local do backend
        csv_file = CSV_PATH
        if not csv_file.exists() and ROOT_CSV_PATH.exists():
            csv_file = ROOT_CSV_PATH

        novo_df.to_csv(csv_file, mode='a', header=not csv_file.exists(), index=False, encoding='utf-8')

        # Se existirem cópias em ambos (backend/ e raiz), sincronizar
        if CSV_PATH.exists() and ROOT_CSV_PATH.exists() and CSV_PATH != ROOT_CSV_PATH:
            try:
                novo_df.to_csv(ROOT_CSV_PATH, mode='a', header=False, index=False, encoding='utf-8')
            except Exception:
                pass

        return {
            "mensagem": "Venda adicionada com sucesso!",
            "registo": novo_registo
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar venda: {str(e)}")

@app.get("/api/exportar-csv")
def exportar_csv(
    cidade: Optional[List[str]] = Query(None),
    produto: Optional[List[str]] = Query(None),
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None
):
    """Gera ficheiro CSV filtrado para descarregamento direto."""
    try:
        df = carregar_dados()
        df_filtrado = filtrar_dataframe(df, cidade, produto, data_inicio, data_fim)
        df_filtrado['data'] = df_filtrado['data'].dt.strftime('%Y-%m-%d')

        csv_content = df_filtrado.to_csv(index=False, encoding='utf-8')
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=relatorio_vendas.csv"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

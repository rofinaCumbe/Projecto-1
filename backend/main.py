"""
API REST de Vendas em FastAPI para deploy no Render.
Processamento de dados com Pandas, cálculo de KPIs e persistência em CSV.
"""

from fastapi import FastAPI, HTTPException, Query, Depends, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime, timedelta
import pandas as pd
import os
import re
import json
import hashlib
import secrets
import urllib.request
import urllib.error

# Carregar variáveis de ambiente do ficheiro .env
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Configuração MongoDB
MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "rofsalesdb")

# Configuração do Assistente de IA (qualquer API compatível com OpenAI: Ollama, Groq, OpenRouter, ...)
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1").rstrip("/")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2:3b")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "120"))
MAX_LINHAS_CONTEXTO_IA = 300

# Conexão global ao MongoDB
mongo_client = None
mongo_db = None

# Fallback: utilizadores em memória (usado quando MongoDB não está acessível)
ADMIN_USERS_FALLBACK = {
    "admin@rofsales.co.mz": {
        "email": "admin@rofsales.co.mz",
        "nome": "Rofina Cumbe",
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "role": "admin"
    },
    "admin@dashboard.co.mz": {
        "email": "admin@dashboard.co.mz",
        "nome": "Administrador",
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "role": "admin"
    }
}

def get_db():
    """Retorna a instância da base de dados MongoDB."""
    global mongo_client, mongo_db
    if mongo_db is not None:
        return mongo_db
    if not MONGODB_URI:
        return None
    try:
        mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        mongo_client.admin.command("ping")
        mongo_db = mongo_client[MONGODB_DB_NAME]
        return mongo_db
    except Exception as e:
        print(f"[AVISO] Erro ao conectar ao MongoDB: {e}")
        return None

def buscar_usuario_db(email: str) -> dict:
    """Busca um utilizador no MongoDB. Se indisponível, usa fallback em memória."""
    db = get_db()
    if db is not None:
        user = db["users"].find_one({"email": email})
        if user:
            return user
    # Fallback: utilizadores em memória
    return ADMIN_USERS_FALLBACK.get(email)

# Tokens de sessão ativos
ACTIVE_TOKENS = {}

app = FastAPI(
    title="Dashboard de Vendas API",
    description="Backend para cálculo de KPIs e gestão de transações de vendas.",
    version="1.0.0"
)

@app.on_event("startup")
def criar_admins_iniciais():
    """Cria os administradores padrão no MongoDB se ainda não existirem."""
    db = get_db()
    if db is None:
        print("[AVISO] MongoDB nao disponivel. Administradores nao foram criados.")
        return

    colecao = db["users"]

    # Criar índice único no campo email
    colecao.create_index("email", unique=True)

    # Lista de administradores iniciais
    admins_padrao = [
        {
            "email": "admin@rofsales.co.mz",
            "nome": "Rofina Cumbe",
            "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
            "role": "admin",
            "criado_em": datetime.now().isoformat()
        },
        {
            "email": "admin@dashboard.co.mz",
            "nome": "Administrador",
            "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
            "role": "admin",
            "criado_em": datetime.now().isoformat()
        }
    ]

    for admin in admins_padrao:
        if not colecao.find_one({"email": admin["email"]}):
            colecao.insert_one(admin)
            print(f"[OK] Admin criado: {admin['email']} ({admin['nome']})")
        else:
            print(f"[INFO] Admin ja existe: {admin['email']}")

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

def calcular_kpis(df_filtrado: pd.DataFrame) -> dict:
    """Calcula os indicadores de negócio e agregados para os gráficos."""
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

class NovaVenda(BaseModel):
    data: str = Field(..., description="Data no formato YYYY-MM-DD")
    produto: str = Field(..., min_length=1)
    cidade: str = Field(..., min_length=1)
    quantidade: int = Field(..., gt=0)
    preco_unitario: float = Field(..., gt=0)
    valor_venda: Optional[float] = None

class LoginRequest(BaseModel):
    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)

def gerar_token():
    return secrets.token_hex(32)

def verificar_token(token: str) -> dict:
    """Verifica se o token é válido e não expirou."""
    if token in ACTIVE_TOKENS:
        dados = ACTIVE_TOKENS[token]
        if datetime.now() < dados["expira_em"]:
            return dados
        else:
            del ACTIVE_TOKENS[token]
    return None

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

@app.post("/api/login")
def fazer_login(dados: LoginRequest):
    """Autenticação de administrador via MongoDB."""
    email = dados.email.strip().lower()
    password_hash = hashlib.sha256(dados.password.encode()).hexdigest()
    
    # Buscar utilizador no MongoDB
    user = buscar_usuario_db(email)
    if not user or user.get("password_hash") != password_hash:
        raise HTTPException(status_code=401, detail="Email ou password incorretos.")
    
    token = gerar_token()
    ACTIVE_TOKENS[token] = {
        "email": email,
        "nome": user["nome"],
        "expira_em": datetime.now() + timedelta(hours=8)
    }
    
    return {
        "token": token,
        "nome": user["nome"],
        "mensagem": "Login efetuado com sucesso!"
    }

@app.get("/api/verificar-token")
def verificar_sessao(token: str = Query(...)):
    """Verifica se o token da sessão ainda é válido."""
    dados = verificar_token(token)
    if not dados:
        raise HTTPException(status_code=401, detail="Sessão expirada ou inválida.")
    return {"valido": True, "nome": dados["nome"], "email": dados["email"]}

@app.post("/api/logout")
def fazer_logout(token: str = Query(...)):
    """Encerra a sessão do administrador."""
    if token in ACTIVE_TOKENS:
        del ACTIVE_TOKENS[token]
    return {"mensagem": "Sessão encerrada com sucesso."}

@app.get("/api/db-status")
def db_status():
    """Verifica a conexão com o MongoDB Atlas."""
    try:
        if not MONGODB_URI:
            return {"status": "não configurado", "mensagem": "MONGODB_URI não definida nas variáveis de ambiente."}
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        db = client[MONGODB_DB_NAME]
        colecoes = db.list_collection_names()
        client.close()
        return {
            "status": "conectado",
            "base_de_dados": MONGODB_DB_NAME,
            "colecoes": colecoes
        }
    except Exception as e:
        return {"status": "erro", "mensagem": str(e)}

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
        return calcular_kpis(df_filtrado)
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


# ==============================================================================
# ASSISTENTE DE IA (modelos open source via API compatível com OpenAI)
# ==============================================================================
class PerguntaIA(BaseModel):
    pergunta: str = Field(..., min_length=3, max_length=500)

PROMPT_SISTEMA_IA = """És um analista de vendas sénior de uma empresa moçambicana.
Respondes sempre em português, de forma clara e objetiva, com valores em Meticais (MZN);
nunca uses R$ nem outra moeda. Usa os totais já calculados no resumo em vez de fazer contas.
Baseia-te APENAS nos dados fornecidos; se a informação não existir nos dados, di-lo.
Responde SEMPRE com um objeto JSON válido, sem texto fora do JSON, com este formato:
{
  "resposta": "resposta direta à pergunta, com números concretos (máx. 120 palavras)",
  "recomendacoes": ["até 3 recomendações práticas para tomada de decisão"],
  "filtros": {"cidade": null, "produto": null, "data_inicio": null, "data_fim": null}
}
Em "filtros", preenche apenas os campos que ajudam a visualizar a resposta na dashboard
(cidade e produto têm de ser exatamente um dos valores disponíveis; datas no formato YYYY-MM-DD);
deixa null os restantes."""

def construir_contexto_ia(df: pd.DataFrame) -> str:
    kpis = calcular_kpis(df)
    cidades = sorted(df['cidade'].dropna().unique().tolist())
    produtos = sorted(df['produto'].dropna().unique().tolist())
    mensal = (
        df.groupby(df['data'].dt.strftime('%Y-%m'))
        .agg(faturamento=('valor_venda', 'sum'), vendas=('valor_venda', 'size'), quantidade=('quantidade', 'sum'))
        .reset_index()
        .rename(columns={'data': 'mes'})
    )
    cidade_produto = (
        df.groupby(['cidade', 'produto'])
        .agg(faturamento=('valor_venda', 'sum'), quantidade=('quantidade', 'sum'))
        .reset_index()
        .sort_values('faturamento', ascending=False)
    )
    recentes = df.sort_values('data', ascending=False).head(MAX_LINHAS_CONTEXTO_IA).copy()
    recentes['data'] = recentes['data'].dt.strftime('%Y-%m-%d')

    resumo = {
        "periodo": {
            "inicio": df['data'].min().strftime('%Y-%m-%d') if not df.empty else None,
            "fim": df['data'].max().strftime('%Y-%m-%d') if not df.empty else None,
        },
        "cidades_disponiveis": cidades,
        "produtos_disponiveis": produtos,
        "kpis": {k: kpis[k] for k in ("faturamento_total", "total_vendas", "quantidade_total", "ticket_medio", "preco_medio_item")},
        "faturamento_por_produto": kpis["ranking_produtos_faturamento"],
        "quantidade_por_produto": kpis["ranking_produtos_quantidade"],
        "faturamento_por_cidade": kpis["faturamento_por_cidade"],
        "evolucao_mensal": mensal.to_dict(orient="records"),
        "faturamento_por_cidade_e_produto": cidade_produto.to_dict(orient="records"),
    }
    return (
        f"RESUMO DOS DADOS (JSON):\n{json.dumps(resumo, ensure_ascii=False, default=float)}\n\n"
        f"TRANSAÇÕES ({len(recentes)} mais recentes de {len(df)}, CSV):\n{recentes.to_csv(index=False)}"
    )

def chamar_llm(mensagens: list) -> str:
    payload = {
        "model": LLM_MODEL,
        "messages": mensagens,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"
    req = urllib.request.Request(
        f"{LLM_BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=LLM_TIMEOUT) as resp:
        dados = json.loads(resp.read().decode("utf-8"))
    return dados["choices"][0]["message"]["content"]

def interpretar_resposta_ia(conteudo: str, cidades: List[str], produtos: List[str]) -> dict:
    try:
        bruto = json.loads(conteudo)
    except json.JSONDecodeError:
        encontrado = re.search(r"\{.*\}", conteudo, re.DOTALL)
        try:
            bruto = json.loads(encontrado.group(0)) if encontrado else {}
        except json.JSONDecodeError:
            bruto = {}
    if not isinstance(bruto, dict) or not bruto.get("resposta"):
        bruto = {"resposta": conteudo.strip()}

    recomendacoes = bruto.get("recomendacoes") or []
    if not isinstance(recomendacoes, list):
        recomendacoes = [recomendacoes]
    recomendacoes = [str(r).strip() for r in recomendacoes if str(r).strip()][:3]

    filtros_brutos = bruto.get("filtros") if isinstance(bruto.get("filtros"), dict) else {}
    mapa_cidades = {c.lower(): c for c in cidades}
    mapa_produtos = {p.lower(): p for p in produtos}
    filtros = {
        "cidade": mapa_cidades.get(str(filtros_brutos.get("cidade") or "").strip().lower()),
        "produto": mapa_produtos.get(str(filtros_brutos.get("produto") or "").strip().lower()),
        "data_inicio": None,
        "data_fim": None,
    }
    for campo in ("data_inicio", "data_fim"):
        valor = str(filtros_brutos.get(campo) or "").strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", valor):
            try:
                datetime.strptime(valor, "%Y-%m-%d")
                filtros[campo] = valor
            except ValueError:
                pass

    return {"resposta": str(bruto["resposta"]).strip(), "recomendacoes": recomendacoes, "filtros": filtros}

@app.post("/api/ia")
def perguntar_ia(dados: PerguntaIA, authorization: Optional[str] = Header(None)):
    """Responde a perguntas em linguagem natural sobre as vendas, com recomendações e filtros sugeridos."""
    token = (authorization or "").removeprefix("Bearer ").strip()
    if not verificar_token(token):
        raise HTTPException(status_code=401, detail="Sessão expirada ou inválida.")

    df = carregar_dados()
    cidades = sorted(df['cidade'].dropna().unique().tolist())
    produtos = sorted(df['produto'].dropna().unique().tolist())
    mensagens = [
        {"role": "system", "content": PROMPT_SISTEMA_IA},
        {"role": "user", "content": f"{construir_contexto_ia(df)}\nPERGUNTA: {dados.pergunta.strip()}"},
    ]

    try:
        conteudo = chamar_llm(mensagens)
    except urllib.error.HTTPError as e:
        detalhe = e.read().decode("utf-8", errors="ignore")[:300]
        raise HTTPException(status_code=502, detail=f"O modelo de IA devolveu um erro ({e.code}): {detalhe}")
    except (urllib.error.URLError, TimeoutError) as e:
        raise HTTPException(
            status_code=503,
            detail=f"Assistente de IA indisponível ({LLM_BASE_URL}). Verifique LLM_BASE_URL, LLM_MODEL e LLM_API_KEY. ({e})",
        )

    return {**interpretar_resposta_ia(conteudo, cidades, produtos), "modelo": LLM_MODEL}

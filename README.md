# Dashboard de Vendas (Projecto 1)

Aplicação completa de análise, diagnóstico e visualização interativa de dados de vendas (contextualizada para Moçambique, moeda em Meticais - MZN), estruturada numa **arquitetura desacoplada e moderna**:
- **Backend**: API REST em **FastAPI + Pandas** pronta para deploy no **Render**.
- **Frontend**: Dashboard moderna e responsiva em **HTML5, Tailwind/CSS, JS e Plotly.js** pronta para deploy no **Vercel**.
- **Modo Local Clássico**: Suporte contínuo a **Streamlit** e scripts CLI.

---

## 🚀 Funcionalidades

- **Diagnóstico e Análise de Dados**: Processamento e cálculo de KPIs de vendas com Pandas.
- **Indicadores de Negócio (KPIs)**: Faturamento total, total de vendas, quantidade vendida, ticket médio e preço médio por item.
- **Visualizações com Plotly**:
  - Faturamento por Produto (gráfico de barras).
  - Distribuição Regional por Cidade (gráfico Donut com percentuais).
  - Evolução Temporal da Receita (gráfico de linha com marcadores).
  - Volume de Vendas por Produto (gráfico de barras horizontais).
- **Filtros Dinâmicos**: Filtragem combinada por Cidade/Praça, Produto e Intervalo de Datas.
- **Entrada de Novos Registos**: Formulário interativo para adicionar novas vendas com cálculo automático do total e persistência em `vendas.csv`.
- **Exportação de Relatórios**: Descarregamento dos dados filtrados em formato CSV.

---

## 📁 Estrutura do Projeto

```text
Projecto1/
├── backend/                        # Backend FastAPI (Deploy no Render)
│   ├── main.py                     # API REST com endpoints de KPIs, filtros e vendas
│   ├── requirements.txt            # Dependências da API (fastapi, uvicorn, pandas, pydantic)
│   └── vendas.csv                  # Base de dados de vendas
│
├── frontend/                       # Frontend estático (Deploy no Vercel)
│   ├── index.html                  # Interface da dashboard com KPIs e gráficos Plotly
│   ├── app.js                      # Lógica de consumo da API, filtros e formulário
│   ├── styles.css                  # Estilos modernos para tema profissional
│   └── config.js                   # Configuração dinâmica do URL da API
│
├── render.yaml                     # Blueprint do Render (1-click deploy)
├── Procfile                        # Comando de inicialização web para o Render
├── vercel.json                     # Roteamento automático de rewrites para o Vercel
│
├── iniciar_backend.bat             # Atalho Windows para iniciar a API FastAPI localmente
├── iniciar_frontend.bat            # Atalho Windows para abrir a dashboard no navegador
├── iniciar_dashboard.bat           # Atalho Windows para iniciar o Streamlit clássico
│
├── app.py                          # Aplicação Streamlit (mantida para uso local)
├── analise_vendas.py               # Script de diagnóstico para o terminal
├── dataset.py                      # Base demográfica moçambicana de clientes
├── requirements.txt                # Dependências gerais do Python
└── README.md                       # Documentação do projeto
```

---

## 🌐 Como Fazer Deploy

### 1. Deploy do Backend no [Render](https://render.com)

1. Aceda ao [Render Dashboard](https://dashboard.render.com/) e faça login.
2. Clique em **"New +"** e selecione **"Web Service"**.
3. Conecte o seu repositório GitHub (`https://github.com/rofinaCumbe/Projecto-1.git`).
4. Configure os parâmetros:
   - **Name**: `dashboard-vendas-backend` (ou o nome que preferir)
   - **Language**: `Python 3`
   - **Branch**: `main`
   - **Root Directory**: deixe vazio (ou `backend`)
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: `Free`
5. Clique em **"Create Web Service"**.
6. Assim que o deploy terminar, copie o URL gerado (ex: `https://dashboard-vendas-backend.onrender.com`).

*(Em alternativa, o Render detectará automaticamente o ficheiro `render.yaml` caso opte por usar o recurso de Blueprints).*

---

### 2. Deploy do Frontend no [Vercel](https://vercel.com)

1. Aceda ao [Vercel Dashboard](https://vercel.com/dashboard) e faça login.
2. Clique em **"Add New..."** e selecione **"Project"**.
3. Importe o repositório GitHub (`Projecto-1`).
4. O Vercel usará as configurações do ficheiro [vercel.json](file:///c:/Users/Rofina%20Cumbe/Documents/Projecto1/vercel.json) já incluído na raiz.
5. Clique em **"Deploy"**.
6. O seu site estará online em segundos (ex: `https://projecto-1.vercel.app`).
7. **Conectar ao Backend**:
   - Abra o site no Vercel.
   - Clique no botão do cabeçalho que indica o status da API (ex: *"A ligar ao Render..."* ou *"Backend Offline"*).
   - Cole o URL do seu backend no Render gerado no passo 1 e clique em **"Salvar URL"**.
   - A dashboard sincronizará imediatamente e guardará a configuração no seu navegador!

---

## 🛠️ Execução no Ambiente Local (Windows)

### Opção A: Executar a Nova Arquitetura (FastAPI + Frontend)
1. Instale as dependências:
   ```bash
   pip install -r backend/requirements.txt
   ```
2. Inicie o backend:
   - Dê duplo clique em `iniciar_backend.bat` (ou execute `uvicorn backend.main:app --reload --port 8000`).
3. Abra o frontend:
   - Dê duplo clique em `iniciar_frontend.bat` (ou abra `frontend/index.html` no navegador).

### Opção B: Executar a Dashboard Streamlit Original
```bash
streamlit run app.py
```
*(ou duplo clique em `iniciar_dashboard.bat`).*

### Opção C: Executar o Diagnóstico no Terminal
```bash
python analise_vendas.py
```
*(ou duplo clique em `executar_analise.bat`).*

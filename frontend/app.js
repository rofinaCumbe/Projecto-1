/**
 * Lógica da Dashboard no Frontend
 * Integração com FastAPI (Render), Plotly.js e Gestão de Estado
 */

let filtrosDisponiveis = { cidades: [], produtos: [], data_minima: "", data_maxima: "" };

function formatarMZN(valor) {
  if (valor === null || valor === undefined || isNaN(valor)) {
    return "0,00 MZN";
  }
  const partes = Number(valor).toFixed(2).split(".");
  const inteiro = partes[0].replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return `${inteiro},${partes[1]} MZN`;
}

function mostrarToast(mensagem, tipo = "success") {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = `toast ${tipo}`;
  toast.innerHTML = `
    <span>${tipo === "success" ? "✅" : "⚠️"}</span>
    <span>${mensagem}</span>
  `;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// ==============================================================================
// GESTÃO DA CONEXÃO COM O BACKEND (RENDER)
// ==============================================================================
async function verificarConexaoBackend() {
  const dot = document.getElementById("status-dot");
  const text = document.getElementById("status-text");
  const banner = document.getElementById("cold-start-banner");
  const apiUrl = getApiBaseUrl();

  // Se demorar mais de 3.5s a responder, alertar sobre o Cold Start do Render
  const coldStartTimer = setTimeout(() => {
    if (dot.className.includes("online")) return;
    banner.style.display = "flex";
    text.textContent = "A acordar o Render...";
  }, 3500);

  try {
    const res = await fetch(`${apiUrl}/health`, { method: "GET" });
    clearTimeout(coldStartTimer);
    banner.style.display = "none";

    if (res.ok) {
      dot.className = "status-dot online";
      const isLocal = apiUrl.includes("localhost") || apiUrl.includes("127.0.0.1");
      text.textContent = isLocal ? "Localhost (8000)" : "Render Conectado";
      return true;
    } else {
      throw new Error("Resposta inválida do backend");
    }
  } catch (err) {
    clearTimeout(coldStartTimer);
    dot.className = "status-dot offline";
    text.textContent = "Backend Offline";
    console.warn("Erro ao conectar ao backend:", err);
    return false;
  }
}

// ==============================================================================
// CARREGAMENTO DE FILTROS E DADOS
// ==============================================================================
function extrairParametrosFiltro() {
  const params = new URLSearchParams();
  const cid = document.getElementById("filtro-cidade").value;
  const prod = document.getElementById("filtro-produto").value;
  const dtIni = document.getElementById("filtro-data-inicio").value;
  const dtFim = document.getElementById("filtro-data-fim").value;

  if (cid) params.append("cidade", cid);
  if (prod) params.append("produto", prod);
  if (dtIni) params.append("data_inicio", dtIni);
  if (dtFim) params.append("data_fim", dtFim);

  return params.toString();
}

async function carregarFiltros() {
  const apiUrl = getApiBaseUrl();
  try {
    const res = await fetch(`${apiUrl}/api/filtros`);
    if (!res.ok) throw new Error("Falha ao carregar filtros");
    filtrosDisponiveis = await res.json();

    // 1. Preencher Select de Cidades
    const selCid = document.getElementById("filtro-cidade");
    const valCid = selCid.value;
    selCid.innerHTML = '<option value="">Todas as Cidades</option>';
    filtrosDisponiveis.cidades.forEach((c) => {
      selCid.innerHTML += `<option value="${c}">${c}</option>`;
    });
    selCid.value = valCid;

    // 2. Preencher Select de Produtos
    const selProd = document.getElementById("filtro-produto");
    const valProd = selProd.value;
    selProd.innerHTML = '<option value="">Todos os Produtos</option>';
    filtrosDisponiveis.produtos.forEach((p) => {
      selProd.innerHTML += `<option value="${p}">${p}</option>`;
    });
    selProd.value = valProd;

    // 3. Preencher selects no modal de nova venda
    const modalCid = document.getElementById("nova-cidade-select");
    modalCid.innerHTML = '<option value="">-- Escolher Existente --</option>';
    filtrosDisponiveis.cidades.forEach((c) => {
      modalCid.innerHTML += `<option value="${c}">${c}</option>`;
    });

    const modalProd = document.getElementById("novo-produto-select");
    modalProd.innerHTML = '<option value="">-- Escolher Existente --</option>';
    filtrosDisponiveis.produtos.forEach((p) => {
      modalProd.innerHTML += `<option value="${p}">${p}</option>`;
    });
  } catch (err) {
    console.error("Erro ao carregar filtros:", err);
  }
}

async function carregarKPIsEGraficos() {
  const apiUrl = getApiBaseUrl();
  const query = extrairParametrosFiltro();
  const url = `${apiUrl}/api/kpis${query ? `?${query}` : ""}`;

  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error("Erro na requisição de KPIs");
    const kpis = await res.json();

    // Atualizar cartões de métricas
    document.getElementById("kpi-faturamento").textContent = formatarMZN(kpis.faturamento_total);
    document.getElementById("kpi-transacoes").textContent = `${kpis.total_vendas} vendas`;
    document.getElementById("kpi-quantidade").textContent = `${kpis.quantidade_total} un`;
    document.getElementById("kpi-ticket").textContent = formatarMZN(kpis.ticket_medio);

    // Renderizar Gráficos Plotly
    renderizarGraficos(kpis);
  } catch (err) {
    console.error("Erro ao carregar KPIs:", err);
  }
}

async function carregarTabelaVendas() {
  const apiUrl = getApiBaseUrl();
  const query = extrairParametrosFiltro();
  const url = `${apiUrl}/api/vendas${query ? `?${query}` : ""}`;
  const tbody = document.getElementById("tabela-vendas-body");
  const totalTxt = document.getElementById("total-registos-txt");

  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error("Erro ao carregar vendas");
    const data = await res.json();

    totalTxt.textContent = `A exibir ${data.total} transações filtradas`;

    if (data.total === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">
            Nenhuma transação encontrada para os filtros selecionados.
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = data.vendas
      .map(
        (v) => `
      <tr>
        <td>${v.data}</td>
        <td><strong>${v.produto}</strong></td>
        <td><span class="badge">${v.cidade}</span></td>
        <td>${v.quantidade} un</td>
        <td>${formatarMZN(v.preco_unitario)}</td>
        <td style="font-weight: 600; color: #60a5fa;">${formatarMZN(v.valor_venda)}</td>
      </tr>
    `
      )
      .join("");
  } catch (err) {
    console.error("Erro na tabela:", err);
    tbody.innerHTML = `
      <tr>
        <td colspan="6" style="text-align: center; color: var(--danger); padding: 2rem;">
          Erro ao carregar as transações da API.
        </td>
      </tr>
    `;
  }
}

// ==============================================================================
// RENDERIZAÇÃO DOS GRÁFICOS (PLOTLY.JS)
// ==============================================================================
const PLOTLY_DARK_LAYOUT = {
  paper_bgcolor: "transparent",
  plot_bgcolor: "transparent",
  font: { color: "#94a3b8", family: "inherit" },
  margin: { t: 30, r: 20, l: 40, b: 40 },
  autosize: true,
  xaxis: { gridcolor: "#334155", zerolinecolor: "#334155" },
  yaxis: { gridcolor: "#334155", zerolinecolor: "#334155" }
};

const PLOTLY_CONFIG = {
  responsive: true,
  displayModeBar: false
};

function renderizarGraficos(kpis) {
  // 1. Gráfico de Faturamento por Produto (Barras)
  const produtosX = kpis.ranking_produtos_faturamento.map((p) => p.produto);
  const produtosY = kpis.ranking_produtos_faturamento.map((p) => p.faturamento);

  const dataFatProd = [
    {
      x: produtosX,
      y: produtosY,
      type: "bar",
      marker: {
        color: ["#3b82f6", "#10b981", "#8b5cf6", "#f59e0b", "#ec4899", "#06b6d4"]
      },
      text: produtosY.map((v) => formatarMZN(v)),
      textposition: "auto"
    }
  ];
  Plotly.react("chart-produto", dataFatProd, { ...PLOTLY_DARK_LAYOUT }, PLOTLY_CONFIG);

  // 2. Gráfico de Faturamento por Cidade (Donut)
  const cidadesNames = kpis.faturamento_por_cidade.map((c) => c.cidade);
  const cidadesValues = kpis.faturamento_por_cidade.map((c) => c.faturamento);

  const dataFatCid = [
    {
      labels: cidadesNames,
      values: cidadesValues,
      type: "pie",
      hole: 0.45,
      textinfo: "label+percent",
      marker: {
        colors: ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#06b6d4"]
      }
    }
  ];
  const donutLayout = {
    ...PLOTLY_DARK_LAYOUT,
    margin: { t: 20, r: 20, l: 20, b: 20 },
    showlegend: false
  };
  Plotly.react("chart-cidade", dataFatCid, donutLayout, PLOTLY_CONFIG);

  // 3. Gráfico de Evolução Temporal (Linha)
  const tempoX = kpis.evolucao_temporal.map((t) => t.data);
  const tempoY = kpis.evolucao_temporal.map((t) => t.faturamento);

  const dataTempo = [
    {
      x: tempoX,
      y: tempoY,
      type: "scatter",
      mode: "lines+markers",
      line: { color: "#3b82f6", width: 3 },
      marker: { size: 7, color: "#60a5fa" }
    }
  ];
  Plotly.react("chart-tempo", dataTempo, { ...PLOTLY_DARK_LAYOUT }, PLOTLY_CONFIG);

  // 4. Gráfico de Quantidade por Produto (Barras Horizontais)
  const qtdReverse = [...kpis.ranking_produtos_quantidade].reverse();
  const qtdX = qtdReverse.map((q) => q.quantidade);
  const qtdY = qtdReverse.map((q) => q.produto);

  const dataVolume = [
    {
      x: qtdX,
      y: qtdY,
      type: "bar",
      orientation: "h",
      marker: { color: "#10b981" },
      text: qtdX.map((q) => `${q} un`),
      textposition: "auto"
    }
  ];
  const volLayout = {
    ...PLOTLY_DARK_LAYOUT,
    margin: { t: 30, r: 20, l: 80, b: 40 }
  };
  Plotly.react("chart-volume", dataVolume, volLayout, PLOTLY_CONFIG);
}

// ==============================================================================
// FILTRAGEM E EXPORTAÇÃO
// ==============================================================================
function aplicarFiltros() {
  carregarKPIsEGraficos();
  carregarTabelaVendas();
}

function limparFiltros() {
  document.getElementById("filtro-cidade").value = "";
  document.getElementById("filtro-produto").value = "";
  document.getElementById("filtro-data-inicio").value = "";
  document.getElementById("filtro-data-fim").value = "";
  aplicarFiltros();
}

function exportarCSV() {
  const apiUrl = getApiBaseUrl();
  const query = extrairParametrosFiltro();
  const url = `${apiUrl}/api/exportar-csv${query ? `?${query}` : ""}`;
  window.open(url, "_blank");
}

// ==============================================================================
// MODAL DE REGISTO DE NOVA VENDA
// ==============================================================================
function abrirModalVenda() {
  document.getElementById("nova-data").value = new Date().toISOString().split("T")[0];
  document.getElementById("modal-venda").classList.add("active");
  calcularTotalPrevisto();
}

function fecharModalVenda() {
  document.getElementById("modal-venda").classList.remove("active");
}

function limparInput(id) {
  const el = document.getElementById(id);
  if (el) el.value = "";
  calcularTotalPrevisto();
}

function limparSelect(id) {
  const el = document.getElementById(id);
  if (el) el.value = "";
  calcularTotalPrevisto();
}

function calcularTotalPrevisto() {
  const qtd = Number(document.getElementById("nova-quantidade").value) || 0;
  const preco = Number(document.getElementById("novo-preco").value) || 0;
  const total = qtd * preco;
  document.getElementById("preview-total").textContent = formatarMZN(total);
}

async function submeterVenda(event) {
  event.preventDefault();
  const btn = document.getElementById("btn-salvar-venda");
  btn.disabled = true;
  btn.textContent = "A gravar...";

  // Resolução da cidade e do produto
  const cidSel = document.getElementById("nova-cidade-select").value;
  const cidCustom = document.getElementById("nova-cidade-custom").value.trim();
  const cidadeFinal = cidCustom || cidSel;

  const prodSel = document.getElementById("novo-produto-select").value;
  const prodCustom = document.getElementById("novo-produto-custom").value.trim();
  const produtoFinal = prodCustom || prodSel;

  if (!cidadeFinal) {
    alert("Por favor, selecione ou digite uma cidade.");
    btn.disabled = false;
    btn.textContent = "💾 Salvar Venda";
    return;
  }

  if (!produtoFinal) {
    alert("Por favor, selecione ou digite um produto.");
    btn.disabled = false;
    btn.textContent = "💾 Salvar Venda";
    return;
  }

  const payload = {
    data: document.getElementById("nova-data").value,
    produto: produtoFinal,
    cidade: cidadeFinal,
    quantidade: parseInt(document.getElementById("nova-quantidade").value, 10),
    preco_unitario: parseFloat(document.getElementById("novo-preco").value)
  };

  const apiUrl = getApiBaseUrl();

  try {
    const res = await fetch(`${apiUrl}/api/vendas`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Falha ao gravar venda");
    }

    mostrarToast(`Venda de ${produtoFinal} guardada com sucesso!`);
    fecharModalVenda();
    document.getElementById("form-nova-venda").reset();

    // Atualizar filtros, KPIs e tabela
    await carregarFiltros();
    aplicarFiltros();
  } catch (err) {
    alert(`Erro ao salvar: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.textContent = "💾 Salvar Venda";
  }
}

// ==============================================================================
// MODAL DE CONFIGURAÇÃO DO BACKEND (RENDER)
// ==============================================================================
function abrirModalConfig() {
  document.getElementById("config-api-url").value = getApiBaseUrl();
  document.getElementById("modal-config").classList.add("active");
}

function fecharModalConfig() {
  document.getElementById("modal-config").classList.remove("active");
}

function guardarConfigAPI() {
  const url = document.getElementById("config-api-url").value.trim();
  setApiBaseUrl(url);
  fecharModalConfig();
  mostrarToast("URL da API atualizado com sucesso!");
  inicializarApp();
}

function restaurarLocalhost() {
  setApiBaseUrl("");
  document.getElementById("config-api-url").value = DEFAULT_LOCAL_API;
  fecharModalConfig();
  mostrarToast("Restaurado para Localhost (8000)");
  inicializarApp();
}

// ==============================================================================
// INICIALIZAÇÃO
// ==============================================================================
async function inicializarApp() {
  const online = await verificarConexaoBackend();
  if (online) {
    await carregarFiltros();
    await carregarKPIsEGraficos();
    await carregarTabelaVendas();
  }
}

document.addEventListener("DOMContentLoaded", () => {
  inicializarApp();
});

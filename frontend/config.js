/**
 * Configuração do Backend (Render ou Localhost)
 */
const DEFAULT_LOCAL_API = "http://localhost:8000";
// Substitua este URL após criar o serviço no Render
const DEFAULT_PROD_API = "https://dashboard-vendas-backend.onrender.com";

function getApiBaseUrl() {
  const savedUrl = localStorage.getItem("API_URL");
  if (savedUrl && savedUrl.trim() !== "") {
    return savedUrl.trim().replace(/\/+$/, "");
  }
  if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
    return DEFAULT_LOCAL_API;
  }
  return DEFAULT_PROD_API;
}

function setApiBaseUrl(url) {
  if (!url || url.trim() === "") {
    localStorage.removeItem("API_URL");
  } else {
    localStorage.setItem("API_URL", url.trim().replace(/\/+$/, ""));
  }
}

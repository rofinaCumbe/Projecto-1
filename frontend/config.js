/**
 * Configuração do Backend (Render ou Localhost)
 */
const DEFAULT_LOCAL_API = "http://localhost:8000";
// URL ativo do Backend no Render
const DEFAULT_PROD_API = "https://projecto-1-inv5.onrender.com";

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

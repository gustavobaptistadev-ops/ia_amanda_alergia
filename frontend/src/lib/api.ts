export async function fetchWithAuth(url: string, options: RequestInit = {}) {
  const headers = new Headers(options.headers || {});
  
  // 1. Injeta Token JWT da sessão se o usuário estiver autenticado
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("token") || sessionStorage.getItem("token");
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  }

  // 2. Injeta a chave de API de serviço interna
  // A autenticação do painel usa exclusivamente o JWT da sessão.
  
  const response = await fetch(url, {
    ...options,
    headers
  });

  if (response.status === 401 && typeof window !== "undefined") {
    localStorage.removeItem("token");
    sessionStorage.removeItem("token");
    window.location.href = "/login";
  }

  return response;
}

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
  headers.set('X-API-Key', process.env.NEXT_PUBLIC_INTERNAL_API_KEY || 'dev-secret-key-123');
  
  return fetch(url, {
    ...options,
    headers
  });
}

export async function fetchWithAuth(url: string, options: RequestInit = {}) {
  const headers = new Headers(options.headers || {});
  headers.set('X-API-Key', process.env.NEXT_PUBLIC_INTERNAL_API_KEY || 'dev-secret-key-123');
  
  return fetch(url, {
    ...options,
    headers
  });
}

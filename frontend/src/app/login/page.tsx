"use client";

import { FormEvent, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("admin@respirar.com");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${apiUrl}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Não foi possível autenticar.");
      localStorage.setItem("token", data.access_token);
      router.replace(searchParams.get("next") || "/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao realizar login.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-4">
      <form onSubmit={handleSubmit} className="w-full max-w-md rounded-2xl bg-white p-8 shadow-2xl">
        <p className="mb-2 text-sm font-semibold uppercase tracking-widest text-blue-600">Clínica Respirar</p>
        <h1 className="mb-2 text-3xl font-bold text-slate-900">Acesso ao painel</h1>
        <p className="mb-8 text-sm text-slate-500">Entre com suas credenciais administrativas.</p>
        <label className="mb-2 block text-sm font-medium text-slate-700">E-mail</label>
        <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" required className="mb-4 w-full rounded-lg border border-slate-300 px-3 py-3 outline-none focus:border-blue-600" />
        <label className="mb-2 block text-sm font-medium text-slate-700">Senha</label>
        <input value={password} onChange={(event) => setPassword(event.target.value)} type="password" required className="mb-4 w-full rounded-lg border border-slate-300 px-3 py-3 outline-none focus:border-blue-600" />
        {error && <p className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        <button disabled={loading} className="w-full rounded-lg bg-blue-600 px-4 py-3 font-semibold text-white hover:bg-blue-700 disabled:opacity-60">{loading ? "Autenticando..." : "Entrar"}</button>
      </form>
    </main>
  );
}

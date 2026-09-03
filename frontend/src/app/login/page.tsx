"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
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
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao realizar login.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#07111f] px-4 py-10">
      <div className="absolute -left-32 -top-32 h-96 w-96 rounded-full bg-blue-500/20 blur-3xl" />
      <div className="absolute -bottom-40 -right-20 h-[30rem] w-[30rem] rounded-full bg-cyan-400/10 blur-3xl" />
      <form onSubmit={handleSubmit} className="relative w-full max-w-[440px] rounded-[28px] border border-white/60 bg-white p-8 shadow-[0_30px_80px_rgba(0,0,0,0.28)] sm:p-10">
        <div className="mb-8 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-blue-600 text-xl font-bold text-white shadow-lg shadow-blue-600/30">R</div>
          <div><p className="text-sm font-bold tracking-[0.18em] text-slate-900">LIFELINE ONE</p><p className="text-[10px] font-semibold tracking-[0.2em] text-slate-400">CLÍNICA MÉDICA</p></div>
        </div>
        <p className="mb-2 text-sm font-semibold text-blue-600">Área restrita</p>
        <h1 className="mb-2 text-3xl font-bold tracking-tight text-slate-950">Acesso ao painel</h1>
        <p className="mb-8 text-sm leading-6 text-slate-500">Entre com suas credenciais para acompanhar a operação da clínica.</p>
        <label className="mb-2 block text-sm font-medium text-slate-700">E-mail</label>
        <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" required className="mb-4 w-full rounded-lg border border-slate-300 px-3 py-3 outline-none focus:border-blue-600" />
        <label className="mb-2 block text-sm font-medium text-slate-700">Senha</label>
        <input value={password} onChange={(event) => setPassword(event.target.value)} type="password" required className="mb-4 w-full rounded-lg border border-slate-300 px-3 py-3 outline-none focus:border-blue-600" />
        {error && <p className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        <button disabled={loading} className="w-full rounded-xl bg-blue-600 px-4 py-3.5 font-semibold text-white shadow-lg shadow-blue-600/20 transition hover:bg-blue-700 disabled:opacity-60">{loading ? "Autenticando..." : "Entrar no painel"}</button>
        <p className="mt-6 text-center text-xs text-slate-400">Acesso protegido por autenticação segura.</p>
      </form>
    </main>
  );
}

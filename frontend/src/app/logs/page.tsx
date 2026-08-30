"use client";
import { fetchWithAuth } from '../../lib/api';

import { 
  Terminal, 
  RefreshCw, 
  Activity, 
  Play, 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  Database, 
  Filter, 
  Search, 
  Loader2,
  Server,
  BellRing,
  Info
} from "lucide-react";
import { useState, useEffect } from "react";

interface LogEntry {
  id: string;
  category: string;
  level: string;
  title: string;
  detail: string;
  created_at: string;
}

interface WorkerStats {
  status: string;
  redis_connected: boolean;
  active_keys: number;
  now: string;
}

export default function LogsPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [stats, setStats] = useState<WorkerStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState("todas");
  const [searchTerm, setSearchTerm] = useState("");
  const [actionMsg, setActionMsg] = useState("");

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

  const fetchLogsAndStats = async () => {
    try {
      const [logsRes, statsRes] = await Promise.all([
        fetchWithAuth(`${apiUrl}/api/v1/logs/?limit=100`),
        fetchWithAuth(`${apiUrl}/api/v1/logs/worker-stats`)
      ]);

      if (logsRes.ok) {
        const logsData = await logsRes.json();
        setLogs(logsData);
      }

      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setStats(statsData);
      }
    } catch (e) {
      console.error("Erro ao buscar logs:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogsAndStats();
    const interval = setInterval(fetchLogsAndStats, 8000); // Polling a cada 8s
    return () => clearInterval(interval);
  }, []);

  const handleTriggerBatch = async () => {
    setTriggering(true);
    setActionMsg("");
    try {
      const res = await fetchWithAuth(`${apiUrl}/api/v1/logs/trigger-reminders`, {
        method: "POST"
      });
      if (res.ok) {
        setActionMsg("Lote de lembretes disparado com sucesso!");
        setTimeout(() => setActionMsg(""), 4000);
        fetchLogsAndStats();
      } else {
        alert("Erro ao disparar lote.");
      }
    } catch (e) {
      alert("Falha na comunicação com o servidor.");
    } finally {
      setTriggering(false);
    }
  };

  const filteredLogs = logs.filter((log) => {
    const matchesCategory = categoryFilter === "todas" || log.category === categoryFilter;
    const matchesSearch = log.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          (log.detail && log.detail.toLowerCase().includes(searchTerm.toLowerCase()));
    return matchesCategory && matchesSearch;
  });

  return (
    <div className="space-y-6 animate-in fade-in duration-500 min-h-screen pb-12">
      {/* Header Superior Responsivo */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h2 className="text-2xl md:text-3xl font-bold text-slate-800 flex items-center gap-3">
            <Terminal className="w-7 h-7 md:w-8 md:h-8 text-blue-600" /> Auditoria & Monitor de Lotes
          </h2>
          <p className="text-slate-500 mt-1 text-xs md:text-sm">
            Acompanhamento em tempo real dos lotes de lembretes, fila Redis e eventos da IA Amanda.
          </p>
        </div>

        <div className="flex items-center gap-2 sm:gap-3">
          <button
            onClick={handleTriggerBatch}
            disabled={triggering}
            className="flex-1 sm:flex-none flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-400 text-white px-4 py-2.5 rounded-xl font-semibold text-xs md:text-sm shadow-sm transition-all"
            title="Executar imediatamente a rotina de lembretes 24h e 2h"
          >
            {triggering ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            Disparar Lote Agora
          </button>

          <button
            onClick={fetchLogsAndStats}
            disabled={loading}
            className="p-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl transition-colors"
            title="Atualizar Logs"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {actionMsg && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-700 text-sm font-semibold rounded-2xl flex items-center gap-2 animate-in slide-in-from-top duration-300">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
          <span>{actionMsg}</span>
        </div>
      )}

      {/* Cards de Métricas e Saúde do Worker */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6">
        <div className="bg-white p-5 md:p-6 rounded-2xl shadow-sm border border-slate-200 flex items-center justify-between">
          <div>
            <p className="text-[10px] md:text-xs font-bold text-slate-400 uppercase tracking-wider">Status do Worker Redis</p>
            <h3 className="text-lg md:text-xl font-bold text-slate-800 mt-1">
              {stats?.redis_connected ? "Operacional & Ativo" : "Desconectado"}
            </h3>
            <p className="text-[11px] text-slate-400 mt-0.5 font-mono">{stats?.now}</p>
          </div>
          <div className={`p-3 md:p-3.5 rounded-2xl ${stats?.redis_connected ? "bg-emerald-50 text-emerald-600" : "bg-rose-50 text-rose-600"}`}>
            <Server className="w-5 h-5 md:w-6 md:h-6" />
          </div>
        </div>

        <div className="bg-white p-5 md:p-6 rounded-2xl shadow-sm border border-slate-200 flex items-center justify-between">
          <div>
            <p className="text-[10px] md:text-xs font-bold text-slate-400 uppercase tracking-wider">Chaves Ativas / Fila</p>
            <h3 className="text-xl md:text-2xl font-bold text-slate-800 mt-1">{stats?.active_keys ?? 0}</h3>
            <p className="text-[11px] text-slate-400 mt-0.5">Memória e checkpoints alocados</p>
          </div>
          <div className="p-3 md:p-3.5 bg-blue-50 text-blue-600 rounded-2xl">
            <Database className="w-5 h-5 md:w-6 md:h-6" />
          </div>
        </div>

        <div className="bg-white p-5 md:p-6 rounded-2xl shadow-sm border border-slate-200 flex items-center justify-between">
          <div>
            <p className="text-[10px] md:text-xs font-bold text-slate-400 uppercase tracking-wider">Cron Job de Lembretes</p>
            <h3 className="text-lg md:text-xl font-bold text-slate-800 mt-1">Recorrente (1h em 1h)</h3>
            <p className="text-[11px] text-emerald-600 font-semibold mt-0.5 flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span> Automático Ativo
            </p>
          </div>
          <div className="p-3 md:p-3.5 bg-purple-50 text-purple-600 rounded-2xl">
            <BellRing className="w-5 h-5 md:w-6 md:h-6" />
          </div>
        </div>
      </div>

      {/* Barra de Filtros e Busca */}
      <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-200 flex flex-col md:flex-row gap-3 md:gap-4 items-center justify-between">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Filtrar por evento ou detalhe..."
            className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-9 pr-4 py-2 text-xs md:text-sm focus:outline-none focus:ring-2 focus:ring-blue-100"
          />
        </div>

        <div className="flex items-center gap-2 w-full md:w-auto">
          <Filter className="w-4 h-4 text-slate-400" />
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="w-full md:w-auto bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs font-semibold text-slate-700 focus:outline-none"
          >
            <option value="todas">Todas as Categorias</option>
            <option value="cron_lembretes">Lembretes & Cron</option>
            <option value="ia_amanda">IA Amanda</option>
            <option value="webhook">Webhook WhatsApp</option>
            <option value="sistema">Sistema & Banco</option>
          </select>
        </div>
      </div>

      {/* Visualização de Logs: CARDS NATIVOS PARA MOBILE (< md) */}
      <div className="block md:hidden space-y-3">
        {filteredLogs.map((l) => (
          <div key={l.id} className="bg-white p-4 rounded-2xl shadow-sm border border-slate-200 space-y-2.5">
            <div className="flex justify-between items-start">
              <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full uppercase ${
                l.level === 'SUCCESS' ? 'bg-emerald-100 text-emerald-700' :
                l.level === 'WARNING' ? 'bg-amber-100 text-amber-700' :
                l.level === 'ERROR' ? 'bg-rose-100 text-rose-700' :
                'bg-blue-100 text-blue-700'
              }`}>
                {l.level}
              </span>
              <span className="text-[11px] font-mono text-slate-400">{l.created_at}</span>
            </div>

            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{l.category.replace('_', ' ')}</p>
              <h4 className="text-sm font-bold text-slate-800 mt-0.5">{l.title}</h4>
            </div>

            {l.detail && (
              <div className="p-2.5 bg-slate-50 rounded-xl border border-slate-100 text-xs font-mono text-slate-600 break-words">
                {l.detail}
              </div>
            )}
          </div>
        ))}

        {filteredLogs.length === 0 && !loading && (
          <div className="bg-white p-8 rounded-2xl border border-slate-200 text-center text-slate-400 text-xs">
            <Activity className="w-10 h-10 mx-auto text-slate-300 mb-2" />
            Nenhum log registrado até o momento.
          </div>
        )}
      </div>

      {/* Visualização de Logs: TABELA CLÁSSICA PARA DESKTOP (>= md) */}
      <div className="hidden md:block bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-600">
            <thead className="bg-slate-50 text-slate-700 text-xs uppercase font-semibold border-b border-slate-200">
              <tr>
                <th className="px-6 py-4">Data & Horário</th>
                <th className="px-6 py-4">Nível</th>
                <th className="px-6 py-4">Categoria</th>
                <th className="px-6 py-4">Evento / Título</th>
                <th className="px-6 py-4">Detalhes Técnicos</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredLogs.map((l) => (
                <tr key={l.id} className="hover:bg-slate-50/70 transition-colors">
                  <td className="px-6 py-4 font-mono text-xs text-slate-500 whitespace-nowrap">
                    {l.created_at}
                  </td>

                  <td className="px-6 py-4">
                    <span className={`text-[11px] font-bold px-2.5 py-1 rounded-full uppercase ${
                      l.level === 'SUCCESS' ? 'bg-emerald-100 text-emerald-700' :
                      l.level === 'WARNING' ? 'bg-amber-100 text-amber-700' :
                      l.level === 'ERROR' ? 'bg-rose-100 text-rose-700' :
                      'bg-blue-100 text-blue-700'
                    }`}>
                      {l.level}
                    </span>
                  </td>

                  <td className="px-6 py-4 font-semibold text-xs text-slate-700 capitalize">
                    {l.category.replace('_', ' ')}
                  </td>

                  <td className="px-6 py-4 font-bold text-slate-800 text-sm">
                    {l.title}
                  </td>

                  <td className="px-6 py-4 text-xs text-slate-500 font-mono max-w-md break-words">
                    {l.detail || "-"}
                  </td>
                </tr>
              ))}

              {filteredLogs.length === 0 && !loading && (
                <tr>
                  <td colSpan={5} className="text-center py-12 text-slate-400 text-sm">
                    <Activity className="w-12 h-12 mx-auto text-slate-300 mb-3" />
                    Nenhum log registrado até o momento.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

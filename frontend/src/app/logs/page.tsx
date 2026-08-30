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
  Trash2,
  Eye,
  Radio
} from "lucide-react";
import { useState, useEffect, useRef } from "react";

interface LiveLog {
  time: string;
  level: string;
  name: string;
  msg: string;
}

interface WorkerStats {
  status: string;
  redis_connected: boolean;
  active_keys: number;
  now: string;
}

export default function LogsPage() {
  const [liveLogs, setLiveLogs] = useState<LiveLog[]>([]);
  const [stats, setStats] = useState<WorkerStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [levelFilter, setLevelFilter] = useState("ALL");
  const [actionMsg, setActionMsg] = useState("");
  const terminalEndRef = useRef<HTMLDivElement>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

  const fetchLogsAndStats = async () => {
    try {
      const [logsRes, statsRes] = await Promise.all([
        fetchWithAuth(`${apiUrl}/api/v1/logs/live`),
        fetchWithAuth(`${apiUrl}/api/v1/logs/worker-stats`)
      ]);

      if (logsRes.ok) {
        const logsData = await logsRes.json();
        setLiveLogs(logsData);
      }

      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setStats(statsData);
      }
    } catch (e) {
      console.error("Erro ao buscar live logs:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogsAndStats();
    const interval = setInterval(fetchLogsAndStats, 3000); // Polling rápido a cada 3s para streaming ao vivo
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (autoScroll) {
      terminalEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [liveLogs, autoScroll]);

  const handleTriggerBatch = async () => {
    setTriggering(true);
    setActionMsg("");
    try {
      const res = await fetchWithAuth(`${apiUrl}/api/v1/logs/trigger-reminders`, {
        method: "POST"
      });
      if (res.ok) {
        setActionMsg("Lote de lembretes disparado com sucesso! Veja a saída no terminal abaixo.");
        setTimeout(() => setActionMsg(""), 5000);
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

  const filteredLogs = liveLogs.filter((log) => {
    const matchesLevel = levelFilter === "ALL" || log.level === levelFilter;
    const matchesSearch = 
      log.msg.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.name.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesLevel && matchesSearch;
  });

  return (
    <div className="space-y-6 animate-in fade-in duration-500 min-h-screen pb-12">
      {/* Header Superior Responsivo */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h2 className="text-2xl md:text-3xl font-bold text-slate-800 flex items-center gap-3">
            <Terminal className="w-7 h-7 md:w-8 md:h-8 text-blue-600" /> Console de Logs & Auditoria Full-Stack
          </h2>
          <p className="text-slate-500 mt-1 text-xs md:text-sm flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            Streaming ao vivo dos logs do servidor FastAPI, LangGraph, Worker Redis e Webhooks.
          </p>
        </div>

        <div className="flex items-center gap-2 sm:gap-3">
          <button
            onClick={handleTriggerBatch}
            disabled={triggering}
            className="flex-1 sm:flex-none flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-400 text-white px-4 py-2.5 rounded-xl font-semibold text-xs md:text-sm shadow-sm transition-all"
            title="Executar imediatamente a rotina de lembretes e ver os logs"
          >
            {triggering ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            Disparar Lote Agora
          </button>

          <button
            onClick={fetchLogsAndStats}
            disabled={loading}
            className="p-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl transition-colors"
            title="Atualizar Logs Manualmente"
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

      {/* JANELA DO TERMINAL / CONSOLE DE LOGS EM TEMPO REAL */}
      <div className="bg-slate-950 rounded-2xl shadow-2xl border border-slate-800 overflow-hidden flex flex-col">
        {/* Barra Superior da Janela de Logs */}
        <div className="bg-slate-900 px-4 py-3 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <div className="flex gap-1.5">
              <div className="w-3 h-3 rounded-full bg-rose-500/80"></div>
              <div className="w-3 h-3 rounded-full bg-amber-500/80"></div>
              <div className="w-3 h-3 rounded-full bg-emerald-500/80"></div>
            </div>
            <span className="text-xs font-mono font-bold text-slate-300 ml-2 flex items-center gap-1.5">
              <Radio className="w-3.5 h-3.5 text-emerald-400 animate-pulse" /> console.live / server-stdout
            </span>
          </div>

          {/* Controles do Terminal: Filtro, Busca e Auto-scroll */}
          <div className="flex items-center gap-2 flex-wrap text-xs">
            <div className="relative w-48">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 transform -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Filtrar console..."
                className="w-full bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded-lg pl-8 pr-2 py-1 focus:outline-none focus:border-blue-500 font-mono"
              />
            </div>

            <select
              value={levelFilter}
              onChange={(e) => setLevelFilter(e.target.value)}
              className="bg-slate-950 border border-slate-800 text-slate-300 text-xs rounded-lg px-2 py-1 focus:outline-none font-mono"
            >
              <option value="ALL">Nível: TODOS</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
            </select>

            <button
              onClick={() => setAutoScroll(!autoScroll)}
              className={`px-2.5 py-1 rounded-lg font-mono text-[11px] flex items-center gap-1 transition-colors ${
                autoScroll ? "bg-blue-600 text-white" : "bg-slate-800 text-slate-400 hover:text-white"
              }`}
            >
              Auto-Scroll: {autoScroll ? "ON" : "OFF"}
            </button>

            <button
              onClick={() => setLiveLogs([])}
              className="p-1 text-slate-500 hover:text-rose-400 transition-colors"
              title="Limpar visualização do console"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Corpo do Terminal com Scroll */}
        <div className="p-4 bg-slate-950 h-96 md:h-[480px] overflow-y-auto font-mono text-xs space-y-1.5 text-slate-300 select-text">
          {filteredLogs.map((log, index) => {
            const isError = log.level === "ERROR" || log.msg.toLowerCase().includes("error") || log.msg.toLowerCase().includes("falha");
            const isWarning = log.level === "WARNING" || log.msg.toLowerCase().includes("warning");
            const isSuccess = log.level === "SUCCESS" || log.msg.toLowerCase().includes("sucesso") || log.msg.toLowerCase().includes("success");

            return (
              <div 
                key={index} 
                className="flex items-start gap-2 hover:bg-slate-900/60 p-1 rounded transition-colors break-all leading-relaxed font-mono"
              >
                <span className="text-slate-500 select-none text-[11px] whitespace-nowrap">[{log.time}]</span>
                
                <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded uppercase whitespace-nowrap ${
                  isError ? "bg-rose-950 text-rose-400 border border-rose-800/50" :
                  isWarning ? "bg-amber-950 text-amber-400 border border-amber-800/50" :
                  isSuccess ? "bg-emerald-950 text-emerald-400 border border-emerald-800/50" :
                  "bg-blue-950 text-blue-400 border border-blue-800/50"
                }`}>
                  {log.level}
                </span>

                <span className="text-slate-400 text-[11px] select-none font-semibold">[{log.name}]</span>

                <span className={
                  isError ? "text-rose-300 font-medium" :
                  isWarning ? "text-amber-300" :
                  isSuccess ? "text-emerald-300" :
                  "text-slate-200"
                }>
                  {log.msg}
                </span>
              </div>
            );
          })}

          {filteredLogs.length === 0 && !loading && (
            <div className="flex flex-col items-center justify-center h-full text-slate-500 space-y-2 py-12">
              <Terminal className="w-8 h-8 text-slate-700" />
              <p>Aguardando novas saídas do servidor ou clique em "Disparar Lote Agora"...</p>
            </div>
          )}

          <div ref={terminalEndRef} />
        </div>
      </div>
    </div>
  );
}

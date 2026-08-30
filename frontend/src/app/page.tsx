"use client";
import { fetchWithAuth } from '../lib/api';

import { Users, Calendar, MessageCircle, ArrowUpRight, TrendingUp, ShieldCheck, Clock, CheckCircle2 } from "lucide-react";
import { useEffect, useState } from "react";

export default function Dashboard() {
  const [analytics, setAnalytics] = useState({
    total_pacientes: 0,
    consultas_agendadas: 0,
    taxa_conversao: "0%",
    atendimentos_humanos: 0,
    total_mensagens: 0,
    lembretes_disparados: 0,
    no_shows_prevenidos_estimados: 0,
    custo_estimado_usd: "$0.000",
    custo_estimado_brl: "R$ 0,00",
    economia_gerada_brl: "R$ 0,00"
  });

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

  useEffect(() => {
    fetchWithAuth(`${apiUrl}/api/v1/analytics/overview`)
      .then(res => res.json())
      .then((json) => setAnalytics(json))
      .catch((err) => console.error("Erro ao buscar analytics:", err));
  }, []);

  const stats = [
    { name: "Total de Pacientes", value: analytics.total_pacientes.toString(), icon: Users, desc: "Cadastrados no sistema", color: "text-blue-600", bg: "bg-blue-50" },
    { name: "Consultas Agendadas", value: analytics.consultas_agendadas.toString(), icon: Calendar, desc: "Agendamentos concluídos", color: "text-emerald-600", bg: "bg-emerald-50" },
    { name: "Taxa de Conversão", value: analytics.taxa_conversao, icon: TrendingUp, desc: "Triagem para Agendamento", color: "text-purple-600", bg: "bg-purple-50" },
    { name: "Custo Estimado IA", value: analytics.custo_estimado_brl, icon: ShieldCheck, desc: `Consumo OpenAI (${analytics.custo_estimado_usd})`, color: "text-amber-600", bg: "bg-amber-50" },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold text-slate-800">Visão Executiva & Custos</h2>
          <p className="text-slate-500 mt-1">Métricas de conversão, eficiência e acompanhamento financeiro de IA em tempo real.</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="bg-emerald-50 border border-emerald-200 px-4 py-2 rounded-xl text-right">
            <p className="text-[11px] font-semibold text-emerald-700 uppercase tracking-wider">Economia Operacional Estimada</p>
            <p className="text-lg font-bold text-emerald-800">{analytics.economia_gerada_brl}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.name} className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 relative overflow-hidden group hover:shadow-md transition-all">
              <div className="flex items-center gap-3 mb-4">
                <div className={`p-3 ${stat.bg} rounded-xl`}>
                  <Icon className={`w-6 h-6 ${stat.color}`} />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-slate-700">{stat.name}</h3>
                  <p className="text-[11px] text-slate-400">{stat.desc}</p>
                </div>
              </div>
              <p className="text-3xl font-bold text-slate-800">{stat.value}</p>
            </div>
          );
        })}
      </div>

      {/* Relatórios de Eficiência & Finanças */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6 space-y-6">
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <h3 className="font-bold text-slate-800 text-lg">Performance & Gastos da IA</h3>
            <span className="text-xs bg-emerald-50 text-emerald-600 font-semibold px-3 py-1 rounded-full">Operação Otimizada</span>
          </div>

          <div className="space-y-4">
            <div className="flex justify-between items-center p-4 bg-slate-50 rounded-xl">
              <div className="flex items-center gap-3">
                <MessageCircle className="w-5 h-5 text-blue-600" />
                <span className="text-sm font-medium text-slate-700">Total de Mensagens Trocadas</span>
              </div>
              <span className="font-bold text-slate-800">{analytics.total_mensagens}</span>
            </div>

            <div className="flex justify-between items-center p-4 bg-slate-50 rounded-xl">
              <div className="flex items-center gap-3">
                <Clock className="w-5 h-5 text-purple-600" />
                <span className="text-sm font-medium text-slate-700">No-Shows Prevenidos (Lembretes)</span>
              </div>
              <span className="font-bold text-slate-800">{analytics.no_shows_prevenidos_estimados}</span>
            </div>

            <div className="flex justify-between items-center p-4 bg-slate-50 rounded-xl">
              <div className="flex items-center gap-3">
                <Users className="w-5 h-5 text-amber-600" />
                <span className="text-sm font-medium text-slate-700">Custo Médio por Mensagem</span>
              </div>
              <span className="font-bold text-slate-800">~R$ 0,004</span>
            </div>
          </div>
        </div>

        <div className="bg-gradient-to-br from-blue-600 to-indigo-700 rounded-2xl shadow-md p-8 text-white flex flex-col justify-between">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 bg-white/20 backdrop-blur-md px-3 py-1.5 rounded-full text-xs font-semibold">
              <CheckCircle2 className="w-4 h-4 text-emerald-300" /> Amanda AI Copilot Ativo
            </div>
            <h3 className="text-2xl font-bold">Atendimento 24/7 com Custo Inteligente</h3>
            <p className="text-blue-100 text-sm leading-relaxed">
              O motor de IA opera com Semantic Caching (Redis) e modelo otimizado (GPT-4o Mini), reduzindo em até 80% o custo de tokens por paciente.
            </p>
          </div>

          <div className="pt-6 border-t border-white/20 flex justify-between items-center text-xs text-blue-200">
            <span>Investimento IA: {analytics.custo_estimado_brl}</span>
            <span>Retorno ROI: ~{analytics.economia_gerada_brl} poupados</span>
          </div>
        </div>
      </div>
    </div>
  );
}

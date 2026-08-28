"use client";
import { fetchWithAuth } from '../lib/api';

import { Users, Calendar, MessageCircle, ArrowUpRight } from "lucide-react";
import { useEffect, useState } from "react";

export default function Dashboard() {
  const [data, setData] = useState({ novos_contatos: 0, agendamentos: 0, em_atendimento: 0 });

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    fetchWithAuth(`${apiUrl}/api/v1/dashboard/stats`)
      .then(res => res.json())
      .then((json) => setData(json))
      .catch((err) => console.error("Erro ao buscar dados da API:", err));
  }, []);

  const stats = [
    { name: "Novos Contatos Hoje", value: data.novos_contatos.toString(), icon: MessageCircle, trend: "+12%" },
    { name: "Agendamentos Concluídos", value: data.agendamentos.toString(), icon: Calendar, trend: "+3" },
    { name: "Pacientes em Atendimento", value: data.em_atendimento.toString(), icon: Users, trend: "" },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.name} className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-4 opacity-10 transform translate-x-4 -translate-y-4 group-hover:scale-110 transition-transform duration-300">
                <Icon className="w-24 h-24 text-blue-600" />
              </div>
              <div className="relative z-10">
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2.5 bg-blue-50 rounded-xl">
                    <Icon className="w-5 h-5 text-blue-600" />
                  </div>
                  <h3 className="text-sm font-medium text-slate-500">{stat.name}</h3>
                </div>
                <div className="flex items-baseline gap-4">
                  <p className="text-4xl font-bold text-slate-800">{stat.value}</p>
                  {stat.trend && (
                    <p className="text-sm font-medium text-emerald-500 flex items-center bg-emerald-50 px-2 py-0.5 rounded-full">
                      <ArrowUpRight className="w-3 h-3 mr-1" />
                      {stat.trend}
                    </p>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6 h-96 flex items-center justify-center">
        <p className="text-slate-400 font-medium">Gráfico de atendimentos semanais conectado ao banco (Em breve)</p>
      </div>
    </div>
  );
}

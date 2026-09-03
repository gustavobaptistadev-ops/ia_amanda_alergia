"use client";
import { fetchWithAuth } from '../../lib/api';

import { MoreHorizontal, MessageSquare, Clock, ShieldCheck, UserCheck } from "lucide-react";
import { useEffect, useState } from "react";
import Link from "next/link";

interface Column {
  title: string;
  color: string;
  patients: string[];
}

export default function Kanban() {
  const [columns, setColumns] = useState<Column[]>([]);

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
    
    const fetchKanban = () => {
      fetchWithAuth(`${apiUrl}/api/v1/dashboard/kanban`)
        .then((res) => res.json())
        .then((data) => setColumns(data))
        .catch((err) => console.error("Erro ao carregar kanban:", err));
    };

    fetchKanban();
    const interval = setInterval(fetchKanban, 10000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="h-full flex flex-col space-y-8 animate-in fade-in duration-500">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-3xl font-bold text-slate-800">Funil Clínico & Kanban</h2>
          <p className="text-slate-500 mt-1">Acompanhamento da jornada de atendimento e triagem médica em tempo real.</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-600 bg-slate-100 px-3 py-1.5 rounded-full border border-slate-200">
            Atualização Automática (10s)
          </span>
        </div>
      </div>

      <div className="flex-1 flex gap-6 overflow-x-auto pb-4">
        {columns.map((col) => (
          <div key={col.title} className="w-80 flex-shrink-0 flex flex-col bg-slate-100/70 rounded-2xl p-4 border border-slate-200/60">
            <div className="flex items-center justify-between mb-4 px-2">
              <div className="flex items-center gap-2">
                <div className={`w-3 h-3 rounded-full ${col.color}`}></div>
                <h3 className="font-bold text-slate-800 text-sm">{col.title}</h3>
                <span className="bg-slate-200 text-slate-700 text-xs font-bold px-2 py-0.5 rounded-full">{col.patients.length}</span>
              </div>
              <button className="text-slate-400 hover:text-slate-600"><MoreHorizontal className="w-4 h-4" /></button>
            </div>
            
            <div className="flex-1 space-y-3 overflow-y-auto pr-1">
              {col.patients.length === 0 ? (
                <div className="border-2 border-dashed border-slate-200 rounded-2xl p-6 text-center text-xs text-slate-400 font-medium">
                  Nenhum paciente nesta etapa
                </div>
              ) : (
                col.patients.map((patient, idx) => (
                  <Link 
                    href="/conversas"
                    key={patient + idx} 
                    className="block bg-white p-4 rounded-2xl shadow-sm border border-slate-200/80 hover:border-blue-300 hover:shadow-md transition-all group"
                  >
                    <div className="flex justify-between items-start mb-2">
                      <p className="font-bold text-slate-800 text-sm group-hover:text-blue-600 transition-colors">{patient}</p>
                      <span className="text-[10px] font-semibold text-blue-700 bg-blue-50 px-2 py-0.5 rounded-md border border-blue-100">
                        WhatsApp
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-xs text-slate-400 mt-3 pt-2 border-t border-slate-100">
                      <span className="flex items-center gap-1 text-[11px] text-emerald-600 font-medium">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                        Amanda IA
                      </span>
                      <span className="text-[11px] text-slate-400 font-medium flex items-center gap-1">
                        <Clock className="w-3 h-3 text-slate-400" /> Ativo
                      </span>
                    </div>
                  </Link>
                ))
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

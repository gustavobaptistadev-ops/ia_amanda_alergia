"use client";
import { MoreHorizontal } from "lucide-react";
import { useEffect, useState } from "react";

interface Column {
  title: string;
  color: string;
  patients: string[];
}

export default function Kanban() {
  const [columns, setColumns] = useState<Column[]>([]);

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    fetch(`${apiUrl}/api/v1/dashboard/kanban`)
      .then((res) => res.json())
      .then((data) => setColumns(data))
      .catch((err) => console.error("Erro ao carregar kanban:", err));
  }, []);

  return (
    <div className="h-full flex flex-col space-y-8 animate-in fade-in duration-500">
      <div>
        <h2 className="text-3xl font-bold text-slate-800">Pacientes</h2>
        <p className="text-slate-500 mt-1">Quadro kanban de acompanhamento em tempo real.</p>
      </div>

      <div className="flex-1 flex gap-6 overflow-x-auto pb-4">
        {columns.map((col) => (
          <div key={col.title} className="w-80 flex-shrink-0 flex flex-col bg-slate-100 rounded-2xl p-4">
            <div className="flex items-center justify-between mb-4 px-2">
              <div className="flex items-center gap-2">
                <div className={`w-3 h-3 rounded-full ${col.color}`}></div>
                <h3 className="font-semibold text-slate-700">{col.title}</h3>
                <span className="bg-slate-200 text-slate-500 text-xs font-bold px-2 py-0.5 rounded-full">{col.patients.length}</span>
              </div>
              <button className="text-slate-400 hover:text-slate-600"><MoreHorizontal className="w-5 h-5" /></button>
            </div>
            
            <div className="flex-1 space-y-3 overflow-y-auto">
              {col.patients.length === 0 ? (
                <div className="border-2 border-dashed border-slate-200 rounded-xl p-4 text-center text-sm text-slate-400 font-medium">
                  Vazio
                </div>
              ) : (
                col.patients.map((patient) => (
                  <div key={patient} className="bg-white p-4 rounded-xl shadow-sm border border-slate-200 cursor-pointer hover:border-blue-300 hover:shadow-md transition-all">
                    <p className="font-semibold text-slate-800">{patient}</p>
                    <p className="text-xs text-slate-400 mt-1 flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                      Ativo agora
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

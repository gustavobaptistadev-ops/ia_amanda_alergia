"use client";
import { Search, Bot, User, CheckCircle2 } from "lucide-react";
import { useState } from "react";

export default function Conversas() {
  const [atendimentoHumano, setAtendimentoHumano] = useState(false);

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col space-y-6 animate-in fade-in duration-500">
      <div>
        <h2 className="text-3xl font-bold text-slate-800">Monitoramento</h2>
        <p className="text-slate-500 mt-1">Acompanhe as conversas da IA Amanda em tempo real.</p>
      </div>

      <div className="flex-1 bg-white rounded-2xl shadow-sm border border-slate-100 flex overflow-hidden">
        {/* Lista de Chats */}
        <div className="w-1/3 border-r border-slate-100 flex flex-col bg-slate-50/50">
          <div className="p-4 border-b border-slate-100">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
              <input type="text" placeholder="Buscar paciente..." className="w-full bg-white border border-slate-200 rounded-full pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-300 transition-all" />
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className={`p-4 rounded-xl flex items-center gap-4 cursor-pointer transition-all ${i === 1 ? 'bg-white shadow-sm border border-slate-100' : 'hover:bg-slate-100/50 border border-transparent'}`}>
                <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-bold text-sm">
                  {i === 1 ? 'CS' : i === 2 ? 'FL' : 'JP'}
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="font-semibold text-slate-800 truncate">{i === 1 ? 'Carlos Silva' : i === 2 ? 'Fernanda Lima' : 'João Pedro'}</h4>
                  <p className="text-xs text-slate-500 truncate">Vou olhar minha agenda...</p>
                </div>
                <span className="text-[10px] text-slate-400 font-medium">10:4{i}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Área da Conversa */}
        <div className="flex-1 flex flex-col bg-slate-50">
          <div className="p-6 border-b border-slate-100 bg-white flex items-center justify-between">
            <div>
              <h3 className="font-bold text-slate-800 text-lg">Carlos Silva</h3>
              <p className={`text-xs font-medium flex items-center gap-1 ${atendimentoHumano ? "text-amber-500" : "text-emerald-500"}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${atendimentoHumano ? "bg-amber-500" : "bg-emerald-500"}`}></span>
                {atendimentoHumano ? "Atendimento Manual (Você)" : "Sendo atendido pela IA"}
              </p>
            </div>
            {!atendimentoHumano && (
              <button 
                onClick={() => setAtendimentoHumano(true)}
                className="text-sm font-medium text-rose-600 bg-rose-50 px-4 py-2 rounded-full hover:bg-rose-100 transition-colors"
              >
                Assumir Atendimento
              </button>
            )}
            {atendimentoHumano && (
              <button 
                onClick={() => setAtendimentoHumano(false)}
                className="text-sm font-medium text-emerald-600 bg-emerald-50 px-4 py-2 rounded-full hover:bg-emerald-100 transition-colors flex items-center gap-1"
              >
                <CheckCircle2 className="w-4 h-4" /> Devolver para IA
              </button>
            )}
          </div>
          
          <div className="flex-1 p-6 overflow-y-auto space-y-6">
            <div className="flex justify-start">
              <div className="bg-white border border-slate-100 p-4 rounded-2xl rounded-tl-sm max-w-[80%] shadow-sm">
                <p className="text-slate-700">Bom dia! Queria saber se vocês atendem Amil e qual o valor da consulta.</p>
                <span className="text-[10px] text-slate-400 mt-2 block">10:40</span>
              </div>
            </div>
            <div className="flex justify-end">
              <div className="bg-blue-600 text-white p-4 rounded-2xl rounded-tr-sm max-w-[80%] shadow-md">
                <p>Olá, Carlos! Que bom falar com você! 😊 Sim, atendemos o convênio Amil perfeitamente. Se preferir a consulta particular, o valor padrão é R$ 650,00.</p>
                <p className="mt-2">Gostaria de verificar os dias disponíveis para você agendar?</p>
                <span className="text-[10px] text-blue-200 mt-2 block text-right">10:41</span>
              </div>
            </div>
            <div className="flex justify-start">
              <div className="bg-white border border-slate-100 p-4 rounded-2xl rounded-tl-sm max-w-[80%] shadow-sm">
                <p className="text-slate-700">Vou olhar minha agenda e já te confirmo.</p>
                <span className="text-[10px] text-slate-400 mt-2 block">10:45</span>
              </div>
            </div>
          </div>
          
          <div className="p-4 bg-white border-t border-slate-100">
            {atendimentoHumano ? (
              <div className="relative">
                <input type="text" placeholder="Digite sua mensagem para Carlos..." className="w-full bg-slate-50 border border-slate-200 rounded-full pl-6 pr-12 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-300 transition-all" />
                <button className="absolute right-3 top-1/2 transform -translate-y-1/2 bg-blue-600 text-white p-1.5 rounded-full hover:bg-blue-700">
                  <User className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <div className="bg-slate-50 border border-slate-200 rounded-full px-4 py-3 text-sm text-slate-400 text-center flex items-center justify-center gap-2">
                <Bot className="w-4 h-4" /> Você está no modo espectador. A IA está conduzindo esta conversa.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

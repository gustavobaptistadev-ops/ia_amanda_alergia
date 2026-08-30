"use client";

import { usePathname } from "next/navigation";
import { Search, Moon, Bell } from "lucide-react";

export default function TopBar() {
  const pathname = usePathname();
  
  const getPageTitle = () => {
    switch (pathname) {
      case "/": return "Dashboard Geral";
      case "/kanban": return "Central de Pacientes";
      case "/conversas": return "Monitoramento de Chats";
      case "/configuracoes": return "Central de Configurações";
      default: return "Painel";
    }
  };

  return (
    <header className="h-16 md:h-20 bg-white border-b border-slate-200 flex items-center justify-between px-4 pl-16 lg:pl-8 lg:px-8">
      <div>
        <p className="text-[10px] md:text-xs text-slate-400 font-medium mb-0.5">Painel Respirar / <span className="capitalize">{pathname.replace('/', '') || 'Dashboard'}</span></p>
        <h2 className="text-base md:text-xl font-bold text-slate-800 truncate max-w-[200px] sm:max-w-none">{getPageTitle()}</h2>
      </div>

      <div className="flex items-center gap-6">
        <div className="relative w-96 hidden md:block">
          <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
          <input 
            type="text" 
            placeholder="Buscar..." 
            className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-10 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-300 transition-all" 
          />
          <div className="absolute right-3 top-1/2 transform -translate-y-1/2 border border-slate-200 rounded px-1.5 py-0.5 text-[10px] text-slate-400 font-bold bg-white">
            ⌘ K
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button className="w-10 h-10 rounded-full hover:bg-slate-100 flex items-center justify-center text-slate-500 transition-colors">
            <Moon className="w-5 h-5" />
          </button>
          <button className="w-10 h-10 rounded-full hover:bg-slate-100 flex items-center justify-center text-slate-500 transition-colors relative">
            <Bell className="w-5 h-5" />
            <span className="absolute top-2 right-2 w-2 h-2 bg-rose-500 rounded-full border-2 border-white"></span>
          </button>
        </div>
      </div>
    </header>
  );
}

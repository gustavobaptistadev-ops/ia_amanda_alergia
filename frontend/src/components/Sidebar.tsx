"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  LayoutDashboard, 
  Users, 
  MessageSquare, 
  Settings, 
  Activity, 
  Database, 
  Calendar, 
  Terminal,
  X,
  Menu
  ,LogOut
} from "lucide-react";
import clsx from "clsx";
import { useState, useEffect } from "react";

export default function Sidebar() {
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);

  function handleLogout() {
    localStorage.removeItem("token");
    sessionStorage.removeItem("token");
    window.location.href = "/login";
  }

  // Fecha a gaveta mobile ao trocar de página
  useEffect(() => {
    setIsOpen(false);
  }, [pathname]);

  const menus = [
    { name: "Dashboard", href: "/", icon: LayoutDashboard },
    { name: "Agenda Médica", href: "/agenda", icon: Calendar },
    { name: "Pacientes", href: "/kanban", icon: Users },
    { name: "Conversas", href: "/conversas", icon: MessageSquare },
    { name: "Conhecimento", href: "/conhecimento", icon: Database },
    { name: "Auditoria & Lotes", href: "/logs", icon: Terminal },
    { name: "Configurações", href: "/configuracoes", icon: Settings },
  ];

  return (
    <>
      {/* Botão Flutuante / Header Hamburger para Mobile (visível apenas em tela pequena) */}
      <div className="lg:hidden fixed top-3 left-4 z-50">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="p-2.5 bg-slate-900 text-white rounded-xl shadow-lg border border-slate-700 flex items-center justify-center hover:bg-slate-800 transition-all"
          aria-label="Abrir Menu"
        >
          {isOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Backdrop escuro quando a sidebar abre no mobile */}
      {isOpen && (
        <div 
          onClick={() => setIsOpen(false)}
          className="lg:hidden fixed inset-0 bg-slate-950/70 backdrop-blur-xs z-40 animate-in fade-in duration-200"
        />
      )}

      {/* Sidebar Principal (Fixa no Desktop e Deslizante no Mobile) */}
      <aside className={clsx(
        "fixed lg:static inset-y-0 left-0 z-50 w-64 bg-slate-900 text-slate-300 flex flex-col border-r border-slate-800 shadow-2xl lg:shadow-none transition-transform duration-300 ease-in-out",
        isOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
      )}>
        {/* Header da Sidebar */}
        <div className="p-6 flex items-center justify-between border-b border-slate-800/50">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-600 rounded-lg text-white">
              <Activity className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-wide">Respirar</h1>
              <p className="text-[10px] text-slate-400 font-medium tracking-widest uppercase">Clínica Médica</p>
            </div>
          </div>

          <button
            onClick={() => setIsOpen(false)}
            className="lg:hidden p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Links de Navegação */}
        <div className="px-4 py-4 flex-1 overflow-y-auto">
          <p className="text-xs font-semibold text-slate-500 mb-4 px-2 uppercase tracking-wider">Operação</p>
          <nav className="space-y-1">
            {menus.map((menu) => {
              const Icon = menu.icon;
              const isActive = pathname === menu.href;
              return (
                <Link
                  key={menu.name}
                  href={menu.href}
                  className={clsx(
                    "flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 text-sm font-medium",
                    isActive 
                      ? "bg-blue-600 text-white shadow-md font-semibold" 
                      : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
                  )}
                >
                  <Icon className={clsx("w-5 h-5", isActive ? "text-white" : "text-slate-400")} />
                  {menu.name}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Perfil do Usuário no Rodapé */}
        <div className="p-4 border-t border-slate-800">
          <div className="flex items-center gap-3 px-2 py-2 rounded-xl hover:bg-slate-800 transition-colors">
            <div className="w-9 h-9 rounded-full bg-blue-600 flex items-center justify-center text-white shadow-lg">
              <span className="font-bold text-xs">GB</span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-slate-200 truncate">Gustavo Baptista</p>
              <p className="text-xs text-slate-500 truncate">Médico(a)</p>
            </div>
            <button onClick={handleLogout} title="Sair" aria-label="Sair" className="rounded-lg p-2 text-slate-400 hover:bg-slate-700 hover:text-white">
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}

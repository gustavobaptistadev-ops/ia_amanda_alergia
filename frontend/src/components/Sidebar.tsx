"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Users, MessageSquare, Settings, Activity } from "lucide-react";
import clsx from "clsx";

export default function Sidebar() {
  const pathname = usePathname();

  const menus = [
    { name: "Dashboard", href: "/", icon: LayoutDashboard },
    { name: "Pacientes", href: "/kanban", icon: Users },
    { name: "Conversas", href: "/conversas", icon: MessageSquare },
    { name: "Configurações", href: "/configuracoes", icon: Settings },
  ];

  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col border-r border-slate-800 shadow-xl">
      <div className="p-6 flex items-center gap-3 border-b border-slate-800/50">
        <div className="p-2 bg-blue-600 rounded-lg text-white">
          <Activity className="w-6 h-6" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-white tracking-wide">Respirar</h1>
          <p className="text-[10px] text-slate-400 font-medium tracking-widest uppercase">Clínica Médica</p>
        </div>
      </div>

      <div className="px-4 py-4">
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
                  "flex items-center gap-3 px-4 py-3 rounded-full transition-all duration-200 text-sm font-medium",
                  isActive 
                    ? "bg-blue-600 text-white shadow-md" 
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

      <div className="mt-auto p-4 border-t border-slate-800">
        <div className="flex items-center gap-3 px-2 py-2 rounded-xl hover:bg-slate-800 cursor-pointer transition-colors">
          <div className="w-9 h-9 rounded-full bg-blue-600 flex items-center justify-center text-white shadow-lg">
            <span className="font-bold text-xs">GB</span>
          </div>
          <div className="flex-1">
            <p className="text-sm font-semibold text-slate-200">Gustavo Baptista</p>
            <p className="text-xs text-slate-500">Médico(a)</p>
          </div>
        </div>
      </div>
    </aside>
  );
}

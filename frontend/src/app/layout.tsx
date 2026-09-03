import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/Sidebar";

const inter = Inter({ subsets: ["latin"] });

import TopBar from "@/components/TopBar";
import AuthGuard from "@/components/AuthGuard";

export const metadata: Metadata = {
  title: "Clínica Respirar | Painel de Controle",
  description: "Sistema de Recepção Inteligente IA Amanda",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <body suppressHydrationWarning className={`${inter.className} bg-slate-50 text-slate-900 flex h-screen overflow-hidden`}>
        <AuthGuard>
          <Sidebar />
          <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
            <TopBar />
            <main className="flex-1 overflow-y-auto bg-slate-50 p-3 sm:p-4 md:p-6 lg:p-8">
              {children}
            </main>
          </div>
        </AuthGuard>
      </body>
    </html>
  );
}

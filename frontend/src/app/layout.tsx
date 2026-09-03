import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

import AuthGuard from "@/components/AuthGuard";

export const metadata: Metadata = {
  title: "Clínica Lifeline One | Painel de Controle",
  description: "Sistema de Recepção Inteligente IA Amanda",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <body suppressHydrationWarning className={`${inter.className} bg-slate-50 text-slate-900`}>
        <AuthGuard>{children}</AuthGuard>
      </body>
    </html>
  );
}

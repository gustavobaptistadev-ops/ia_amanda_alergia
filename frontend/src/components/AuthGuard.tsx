"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import Sidebar from "@/components/Sidebar";
import TopBar from "@/components/TopBar";

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [checking, setChecking] = useState(true);
  const isPublicRoute = pathname === "/login" || (typeof window !== "undefined" && window.location.pathname === "/login");

  useEffect(() => {
    if (isPublicRoute) {
      setChecking(false);
      return;
    }

    const token = localStorage.getItem("token") || sessionStorage.getItem("token");
    if (!token) {
      router.replace("/login");
      return;
    }

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";
    fetch(`${apiUrl}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then((response) => {
      if (!response.ok) {
        localStorage.removeItem("token");
        sessionStorage.removeItem("token");
        router.replace("/login");
        return;
      }
      setChecking(false);
    }).catch(() => router.replace("/login"));
  }, [isPublicRoute, pathname, router]);

  if (checking && !isPublicRoute) {
    return <div className="flex min-h-screen items-center justify-center bg-slate-50 text-slate-500">Validando sessão...</div>;
  }

  if (isPublicRoute) return <>{children}</>;

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50 text-slate-900">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <TopBar />
        <main className="flex-1 overflow-y-auto bg-slate-50 p-3 sm:p-4 md:p-6 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}

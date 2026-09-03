"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

const PUBLIC_PATHS = ["/login"];

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    if (PUBLIC_PATHS.includes(pathname)) {
      setChecking(false);
      return;
    }

    const token = localStorage.getItem("token") || sessionStorage.getItem("token");
    if (!token) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
      return;
    }

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";
    fetch(`${apiUrl}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then((response) => {
      if (!response.ok) {
        localStorage.removeItem("token");
        sessionStorage.removeItem("token");
        router.replace(`/login?next=${encodeURIComponent(pathname)}`);
        return;
      }
      setChecking(false);
    }).catch(() => router.replace("/login"));
  }, [pathname, router]);

  if (checking && !PUBLIC_PATHS.includes(pathname)) {
    return <div className="flex min-h-screen items-center justify-center bg-slate-50 text-slate-500">Validando sessão...</div>;
  }

  return <>{children}</>;
}

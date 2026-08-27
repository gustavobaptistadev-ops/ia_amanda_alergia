"use client";
import { QrCode, Smartphone, RefreshCw, Key, CheckCircle2, AlertCircle } from "lucide-react";
import { useState, useEffect } from "react";
import Image from "next/image";

export default function Configuracoes() {
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [qrCodeBase64, setQrCodeBase64] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fetchStatusAndQr = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      // Verifica o status
      const statusRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'}/api/v1/evolution/status`);
      if (statusRes.ok) {
        const statusData = await statusRes.json();
        const state = statusData.state || statusData.instance?.state || statusData.instance?.status;
        const ghosthubLoggedIn = statusData.data?.LoggedIn;
        
        if (state === "open" || state === "CONNECTED" || state === "connected" || ghosthubLoggedIn === true) {
          setSuccess(true);
          setLoading(false);
          return;
        }
      }

      // Se não está conectado, busca o QR Code
      const qrRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'}/api/v1/evolution/qr`);
      if (qrRes.ok) {
        const qrData = await qrRes.json();
        if (qrData.error) {
          setErrorMsg(qrData.message || "Erro retornado pela provedora ao gerar QR.");
        } else if (qrData.base64) {
          setQrCodeBase64(qrData.base64);
        } else if (qrData.qrcode) {
          setQrCodeBase64(qrData.qrcode);
        } else if (qrData.data?.Qrcode) {
          setQrCodeBase64(qrData.data.Qrcode);
        } else {
          setErrorMsg("QR Code veio vazio da provedora.");
        }
      } else {
        setErrorMsg("Não foi possível carregar o QR Code.");
      }
    } catch (error) {
      setErrorMsg("Erro ao conectar com o servidor.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatusAndQr();
  }, []);

  const handleGenerateQR = () => {
    fetchStatusAndQr();
  };

  return (
    <div className="flex justify-center items-start pt-10 animate-in fade-in duration-500 min-h-screen">
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 space-y-6 w-full max-w-md">
        <div className="flex items-center gap-4 border-b border-slate-100 pb-4">
          <div className="p-3 bg-blue-50 rounded-xl">
            <Smartphone className="w-6 h-6 text-blue-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-slate-800">Conexão WhatsApp</h3>
            <p className="text-sm text-slate-500">Evolution GO</p>
          </div>
        </div>
        
        <div className="flex flex-col items-center justify-center p-6 bg-slate-50 rounded-xl border-2 border-dashed border-slate-200 min-h-[300px]">
          {success ? (
            <div className="flex flex-col items-center animate-in zoom-in duration-300 w-full">
              <CheckCircle2 className="w-20 h-20 text-emerald-500 mb-4" />
              <p className="text-slate-700 font-medium text-lg">Conectado!</p>
              <p className="text-xs text-slate-400 mt-1 text-center mb-6">A IA já está operando.</p>
              
              <div className="flex flex-col gap-3 w-full border-t border-slate-200 pt-5">
                <button
                  onClick={async () => {
                    if (!confirm("Reiniciar a conexão?")) return;
                    setLoading(true);
                    try {
                      await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'}/api/v1/evolution/restart`, { method: "PUT" });
                      setTimeout(() => fetchStatusAndQr(), 3000);
                    } catch (e) {
                      alert("Erro ao reiniciar.");
                    }
                    setLoading(false);
                  }}
                  disabled={loading}
                  className="flex items-center justify-center gap-2 bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 disabled:bg-slate-100 px-4 py-2 rounded-lg font-medium shadow-sm text-sm"
                >
                  <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
                  Reiniciar
                </button>
                
                <button
                  onClick={async () => {
                    if (!confirm("Desconectar o WhatsApp?")) return;
                    setLoading(true);
                    try {
                      await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'}/api/v1/evolution/logout`, { method: "DELETE" });
                      setTimeout(() => fetchStatusAndQr(), 2000);
                    } catch (e) {
                      alert("Erro ao desconectar.");
                    }
                    setLoading(false);
                  }}
                  disabled={loading}
                  className="flex items-center justify-center gap-2 bg-rose-50 border border-rose-200 text-rose-600 hover:bg-rose-100 px-4 py-2 rounded-lg font-medium shadow-sm text-sm"
                >
                  <AlertCircle className="w-4 h-4" />
                  Desconectar
                </button>
              </div>
            </div>
          ) : (
            <>
              {qrCodeBase64 ? (
                <div className="mb-4 bg-white p-3 rounded-2xl shadow-sm border border-slate-100">
                  <Image src={qrCodeBase64} alt="QR Code" width={200} height={200} className="rounded-lg" />
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center bg-slate-100/50 rounded-2xl w-40 h-40 mb-5 border border-slate-200/50">
                  <QrCode className="w-12 h-12 text-slate-300 mb-2" />
                  <span className="text-[11px] text-slate-400 font-medium">Aguardando QR</span>
                </div>
              )}
              
              {errorMsg && (
                <div className="flex items-center gap-2 text-rose-600 bg-rose-50 px-3 py-2 rounded-lg text-xs mb-5 w-full justify-center border border-rose-100 text-center">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span className="font-medium">{errorMsg}</span>
                </div>
              )}

              <button 
                onClick={handleGenerateQR}
                disabled={loading}
                className="flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white w-full py-2.5 rounded-lg font-medium shadow-sm text-sm"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
                {loading ? "Carregando..." : "Gerar QR Code"}
              </button>
              <p className="text-[11px] text-slate-500 mt-4 text-center">
                Vá em Aparelhos Conectados no seu celular.
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

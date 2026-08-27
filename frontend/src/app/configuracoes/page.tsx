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
    <div className="space-y-8 animate-in fade-in duration-500 max-w-4xl">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 space-y-6">
          <div className="flex items-center gap-4 border-b border-slate-100 pb-4">
            <div className="p-3 bg-blue-50 rounded-xl">
              <Smartphone className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-slate-800">Conexão WhatsApp (Evolution GO)</h3>
              <p className="text-sm text-slate-500">Leia o QR Code para conectar</p>
            </div>
          </div>
          
          <div className="flex flex-col items-center justify-center p-8 bg-slate-50 rounded-xl border-2 border-dashed border-slate-200 min-h-[300px]">
            {success ? (
              <div className="flex flex-col items-center animate-in zoom-in duration-300 w-full">
                <CheckCircle2 className="w-24 h-24 text-emerald-500 mb-4" />
                <p className="text-slate-700 font-medium text-lg">WhatsApp Conectado!</p>
                <p className="text-sm text-slate-400 mt-1 text-center mb-8">A IA Amanda já pode responder seus pacientes.</p>
                
                <div className="flex gap-4 w-full justify-center border-t border-slate-200 pt-6">
                  <button
                    onClick={async () => {
                      if (!confirm("Tem certeza que deseja reiniciar a conexão?")) return;
                      setLoading(true);
                      try {
                        await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'}/api/v1/evolution/restart`, { method: "PUT" });
                        setTimeout(() => fetchStatusAndQr(), 3000); // aguarda um pouco e recarrega
                      } catch (e) {
                        alert("Erro ao reiniciar a conexão.");
                      }
                      setLoading(false);
                    }}
                    disabled={loading}
                    className="flex items-center gap-2 bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 disabled:bg-slate-100 disabled:cursor-not-allowed px-5 py-2 rounded-xl font-medium transition-colors shadow-sm text-sm"
                  >
                    <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
                    Reiniciar
                  </button>
                  
                  <button
                    onClick={async () => {
                      if (!confirm("Tem certeza que deseja desconectar o WhatsApp? Você precisará ler o QR Code novamente.")) return;
                      setLoading(true);
                      try {
                        await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'}/api/v1/evolution/logout`, { method: "DELETE" });
                        setTimeout(() => fetchStatusAndQr(), 2000);
                      } catch (e) {
                        alert("Erro ao desconectar o WhatsApp.");
                      }
                      setLoading(false);
                    }}
                    disabled={loading}
                    className="flex items-center gap-2 bg-rose-50 border border-rose-200 text-rose-600 hover:bg-rose-100 disabled:bg-slate-100 disabled:cursor-not-allowed px-5 py-2 rounded-xl font-medium transition-colors shadow-sm text-sm"
                  >
                    <AlertCircle className="w-4 h-4" />
                    Desconectar
                  </button>
                </div>
              </div>
            ) : (
              <>
                {qrCodeBase64 ? (
                  <div className="mb-4 bg-white p-4 rounded-2xl shadow-sm border border-slate-100">
                    <Image src={qrCodeBase64} alt="QR Code WhatsApp" width={220} height={220} className="rounded-lg" />
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center bg-slate-100/50 rounded-2xl w-48 h-48 mb-6 border border-slate-200/50">
                    <QrCode className="w-16 h-16 text-slate-300 mb-2" />
                    <span className="text-xs text-slate-400 font-medium">Aguardando QR Code</span>
                  </div>
                )}
                
                {errorMsg && (
                  <div className="flex items-center gap-2 text-rose-600 bg-rose-50 px-4 py-3 rounded-xl text-sm mb-6 w-full justify-center border border-rose-100">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    <p className="font-medium">{errorMsg}</p>
                  </div>
                )}

                <button 
                  onClick={handleGenerateQR}
                  disabled={loading}
                  className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed text-white px-8 py-3 rounded-xl font-medium transition-all shadow-sm shadow-blue-600/20 active:scale-95"
                >
                  <RefreshCw className={`w-5 h-5 ${loading ? "animate-spin" : ""}`} />
                  {loading ? "Carregando..." : "Gerar QR Code"}
                </button>
                <p className="text-sm text-slate-500 mt-6 text-center max-w-xs leading-relaxed">
                  Abra o WhatsApp no seu celular, vá em <span className="font-semibold text-slate-700">Aparelhos Conectados</span> e aponte a câmera.
                </p>
              </>
            )}
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 space-y-6">
          <div className="flex items-center gap-4 border-b border-slate-100 pb-4">
            <div className="p-3 bg-emerald-50 rounded-xl">
              <Key className="w-6 h-6 text-emerald-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-slate-800">Credenciais</h3>
              <p className="text-sm text-slate-500">Variáveis de ambiente (Ocultas)</p>
            </div>
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">OpenAI API Key</label>
              <input type="password" value="••••••••••••••••••••••••••••••••" readOnly className="w-full bg-slate-50 border border-slate-200 rounded-lg px-4 py-2.5 text-slate-400 focus:outline-none cursor-not-allowed select-none" />
              <p className="text-xs text-slate-400 mt-1">Configurado de forma segura no Railway.</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Evolution API URL</label>
              <input type="password" value="••••••••••••••••••••••••••••••••" readOnly className="w-full bg-slate-50 border border-slate-200 rounded-lg px-4 py-2.5 text-slate-400 focus:outline-none cursor-not-allowed select-none" />
              <p className="text-xs text-slate-400 mt-1">Configurado de forma segura no Railway.</p>
            </div>
          </div>
        </div>
      </div>

      {/* Zona de Risco */}
      <div className="bg-rose-50 border border-rose-200 rounded-2xl p-6 mt-12 animate-in fade-in">
        <h3 className="text-rose-600 font-bold flex items-center gap-2 mb-2">
          <span className="text-xl">⚠️</span> Zona de Risco
        </h3>
        <p className="text-sm text-rose-600/80 mb-6">
          Ações irreversíveis — use apenas em ambiente de testes ou quando precisar recomeçar do zero.
        </p>

        <div className="flex items-center justify-between border-t border-rose-200/50 pt-4 mt-4">
          <div>
            <h4 className="font-semibold text-slate-800">Apagar todas as conversas</h4>
            <p className="text-xs text-slate-500 mt-1 max-w-xl">
              Remove permanentemente do banco e da memória da IA: todos os pacientes/leads, fichas cadastrais, conversas, agendamentos e contexto acumulado no Redis.
            </p>
          </div>
          <button className="bg-white border border-rose-200 text-rose-600 hover:bg-rose-100 font-medium px-4 py-2.5 rounded-lg text-sm transition-colors shadow-sm">
            Resetar banco de dados
          </button>
        </div>
      </div>
    </div>
  );
}

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
        if (statusData.state === "open" || statusData.state === "CONNECTED") {
          setSuccess(true);
          setLoading(false);
          return;
        }
      }

      // Se não está conectado, busca o QR Code
      const qrRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'}/api/v1/evolution/qr`);
      if (qrRes.ok) {
        const qrData = await qrRes.json();
        if (qrData.base64) {
          setQrCodeBase64(qrData.base64);
        } else if (qrData.qrcode) {
          setQrCodeBase64(qrData.qrcode);
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
              <div className="flex flex-col items-center animate-in zoom-in duration-300">
                <CheckCircle2 className="w-32 h-32 text-emerald-500 mb-4" />
                <p className="text-slate-700 font-medium text-lg">WhatsApp Conectado!</p>
                <p className="text-sm text-slate-400 mt-1 text-center">A IA Amanda já pode responder seus pacientes.</p>
              </div>
            ) : (
              <>
                {qrCodeBase64 ? (
                  <div className="mb-4 bg-white p-2 rounded-xl shadow-sm">
                    <Image src={qrCodeBase64} alt="QR Code WhatsApp" width={180} height={180} className="rounded-lg" />
                  </div>
                ) : (
                  <QrCode className="w-40 h-40 text-slate-300 mb-4" />
                )}
                
                {errorMsg && (
                  <div className="flex items-center gap-2 text-rose-500 text-sm mb-4">
                    <AlertCircle className="w-4 h-4" />
                    <p>{errorMsg}</p>
                  </div>
                )}

                <button 
                  onClick={handleGenerateQR}
                  disabled={loading}
                  className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed text-white px-6 py-2.5 rounded-full font-medium transition-colors"
                >
                  <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
                  {loading ? "Carregando..." : "Gerar QR Code"}
                </button>
                <p className="text-xs text-slate-400 mt-4 text-center">
                  Abra o WhatsApp no seu celular, vá em Aparelhos Conectados e aponte a câmera.
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

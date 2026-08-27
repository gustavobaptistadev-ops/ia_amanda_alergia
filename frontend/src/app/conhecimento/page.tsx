"use client";
import { Database, Save, Loader2, FileText, CheckCircle2 } from "lucide-react";
import { useState, useEffect } from "react";

export default function Conhecimento() {
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    const fetchRag = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
        const res = await fetch(`${apiUrl}/api/v1/rag/`);
        if (res.ok) {
          const data = await res.json();
          setContent(data.content);
        }
      } catch (err) {
        console.error("Erro ao carregar RAG", err);
      } finally {
        setLoading(false);
      }
    };
    fetchRag();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setSuccess(false);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
      const res = await fetch(`${apiUrl}/api/v1/rag/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ content }),
      });
      
      if (res.ok) {
        setSuccess(true);
        setTimeout(() => setSuccess(false), 3000);
      } else {
        alert("Erro ao salvar a base de conhecimento.");
      }
    } catch (err) {
      console.error(err);
      alert("Falha na comunicação com o servidor.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500 max-w-5xl">
      <div>
        <h2 className="text-3xl font-bold text-slate-800 flex items-center gap-3">
          <Database className="w-8 h-8 text-blue-600" />
          Base de Conhecimento (RAG)
        </h2>
        <p className="text-slate-500 mt-2 max-w-2xl">
          Tudo que você digitar aqui será absorvido pelo "cérebro" da IA Amanda. 
          Use este espaço para cadastrar regras de negócio, preços de consultas, convênios aceitos, 
          especialidades da clínica e endereço. Sempre que a IA tiver uma dúvida, ela lerá este documento.
        </p>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-[600px]">
        <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex justify-between items-center">
          <div className="flex items-center gap-2 text-slate-700 font-semibold">
            <FileText className="w-5 h-5 text-slate-400" />
            Editor de Regras da Clínica
          </div>
          
          <button 
            onClick={handleSave}
            disabled={saving || loading}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white px-5 py-2 rounded-lg font-medium transition-colors shadow-sm"
          >
            {saving ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Treinando IA...
              </>
            ) : success ? (
              <>
                <CheckCircle2 className="w-4 h-4" />
                Salvo e Treinado!
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                Salvar e Treinar IA
              </>
            )}
          </button>
        </div>
        
        <div className="flex-1 p-6 relative">
          {loading ? (
            <div className="absolute inset-0 flex items-center justify-center bg-white/80 z-10">
              <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
            </div>
          ) : null}
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Digite aqui as regras da clínica, convênios aceitos, endereço, preços..."
            className="w-full h-full resize-none outline-none text-slate-700 text-base leading-relaxed bg-transparent"
          />
        </div>
      </div>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";

export default function AprendizadoPage() {
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchSuggestions = async () => {
    try {
      const res = await fetch("/api/v1/learning/", {
        headers: { "x-api-key": "sk_amanda_9f8d7e6c5b4a3f2e1d0c9b8a7f6e5d4c" }
      });
      const data = await res.json();
      if (Array.isArray(data)) {
        setSuggestions(data);
      }
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSuggestions();
  }, []);

  const handleApprove = async (id: string) => {
    try {
      await fetch(`/api/v1/learning/${id}/approve`, {
        method: "POST",
        headers: { "x-api-key": "sk_amanda_9f8d7e6c5b4a3f2e1d0c9b8a7f6e5d4c" }
      });
      fetchSuggestions();
    } catch (e) {
      alert("Erro ao aprovar");
    }
  };

  const handleReject = async (id: string) => {
    try {
      await fetch(`/api/v1/learning/${id}/reject`, {
        method: "POST",
        headers: { "x-api-key": "sk_amanda_9f8d7e6c5b4a3f2e1d0c9b8a7f6e5d4c" }
      });
      fetchSuggestions();
    } catch (e) {
      alert("Erro ao rejeitar");
    }
  };

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">Aprendizado Contínuo da IA</h1>
      <p className="text-gray-600 mb-8">Sugestões de melhoria extraídas automaticamente das conversas recentes.</p>
      
      {loading ? (
        <p>Carregando sugestões...</p>
      ) : suggestions.length === 0 ? (
        <p className="text-gray-500">Nenhuma sugestão pendente no momento.</p>
      ) : (
        <div className="space-y-4">
          {suggestions.map((s) => (
            <div key={s.id} className="p-6 bg-white rounded-lg border shadow-sm flex flex-col gap-2">
              <div className="flex justify-between items-center">
                <span className="font-semibold text-lg text-blue-600">Paciente: {s.patient_name}</span>
                <span className="text-sm text-gray-500">{new Date(s.created_at).toLocaleString()}</span>
              </div>
              
              <div className="bg-gray-50 p-4 rounded text-gray-800 italic">
                "{s.context}"
              </div>
              
              <div className="mt-2 text-gray-900">
                <strong>Sugestão da IA:</strong> {s.suggestion_text}
              </div>
              
              <div className="flex gap-4 mt-4">
                <button 
                  onClick={() => handleApprove(s.id)}
                  className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 transition"
                >
                  Aprovar & Treinar IA
                </button>
                <button 
                  onClick={() => handleReject(s.id)}
                  className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition"
                >
                  Rejeitar Sugestão
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

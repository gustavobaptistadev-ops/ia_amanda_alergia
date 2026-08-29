"use client";
import { fetchWithAuth } from '../../lib/api';
import { Database, Save, Loader2, FileText, CheckCircle2, Plus, Trash2, Zap } from "lucide-react";
import { useState, useEffect } from "react";

interface RagFile {
  filename: string;
  content: string;
}

export default function Conhecimento() {
  const [files, setFiles] = useState<RagFile[]>([]);
  const [activeFile, setActiveFile] = useState<RagFile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [training, setTraining] = useState(false);
  const [success, setSuccess] = useState(false);
  const [trainSuccess, setTrainSuccess] = useState(false);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

  const fetchFiles = async () => {
    try {
      const res = await fetchWithAuth(`${apiUrl}/api/v1/rag/`);
      if (res.ok) {
        const data = await res.json();
        setFiles(data);
        if (data.length > 0 && !activeFile) {
          setActiveFile(data[0]);
        } else if (activeFile) {
          const updated = data.find((f: RagFile) => f.filename === activeFile.filename);
          if (updated) setActiveFile(updated);
        }
      }
    } catch (err) {
      console.error("Erro ao carregar arquivos do RAG", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFiles();
  }, []);

  const handleSave = async () => {
    if (!activeFile) return;
    setSaving(true);
    setSuccess(false);
    try {
      const res = await fetchWithAuth(`${apiUrl}/api/v1/rag/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename: activeFile.filename, content: activeFile.content }),
      });
      if (res.ok) {
        setSuccess(true);
        setTimeout(() => setSuccess(false), 3000);
        await fetchFiles();
      } else {
        alert("Erro ao salvar o documento.");
      }
    } catch (err) {
      console.error(err);
      alert("Falha na comunicação com o servidor.");
    } finally {
      setSaving(false);
    }
  };

  const handleTrain = async () => {
    setTraining(true);
    setTrainSuccess(false);
    try {
      const res = await fetchWithAuth(`${apiUrl}/api/v1/rag/train`, { method: "POST" });
      if (res.ok) {
        setTrainSuccess(true);
        setTimeout(() => setTrainSuccess(false), 3000);
      } else {
        alert("Erro ao treinar a IA.");
      }
    } catch (err) {
      console.error(err);
      alert("Falha na comunicação com o servidor ao treinar.");
    } finally {
      setTraining(false);
    }
  };

  const handleCreateFile = () => {
    const filename = prompt("Digite o nome do novo documento (ex: precos_exames.md):");
    if (!filename) return;
    const newFile = { filename: filename.endsWith('.md') ? filename : `${filename}.md`, content: "# Novo Documento\n" };
    setFiles([...files, newFile]);
    setActiveFile(newFile);
  };

  const handleDeleteFile = async (filename: string) => {
    if (!confirm(`Tem certeza que deseja apagar ${filename}?`)) return;
    try {
      const res = await fetchWithAuth(`${apiUrl}/api/v1/rag/${filename}`, { method: "DELETE" });
      if (res.ok) {
        if (activeFile?.filename === filename) {
          setActiveFile(null);
        }
        await fetchFiles();
      } else {
        alert("Erro ao deletar documento.");
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col space-y-6 animate-in fade-in duration-500">
      <div className="flex justify-between items-end">
        <div>
          <h2 className="text-3xl font-bold text-slate-800 flex items-center gap-3">
            <Database className="w-8 h-8 text-blue-600" />
            Base de Conhecimento (RAG)
          </h2>
          <p className="text-slate-500 mt-2 max-w-2xl">
            Gerencie os documentos que a IA lê. Adicione regras, preços e protocolos. Após editar os arquivos, clique em Treinar IA.
          </p>
        </div>
        <button 
          onClick={handleTrain}
          disabled={training}
          className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-400 text-white px-6 py-3 rounded-xl font-bold transition-all shadow-md hover:shadow-lg"
        >
          {training ? (
            <><Loader2 className="w-5 h-5 animate-spin" /> Treinando...</>
          ) : trainSuccess ? (
            <><CheckCircle2 className="w-5 h-5" /> IA Treinada!</>
          ) : (
            <><Zap className="w-5 h-5" /> Treinar IA Agora</>
          )}
        </button>
      </div>

      <div className="flex-1 bg-white rounded-2xl shadow-sm border border-slate-100 flex overflow-hidden">
        {/* Sidebar de Arquivos */}
        <div className="w-64 border-r border-slate-100 flex flex-col bg-slate-50/50">
          <div className="p-4 border-b border-slate-100 flex justify-between items-center bg-slate-100/50">
            <span className="font-semibold text-slate-700 text-sm">Documentos</span>
            <button onClick={handleCreateFile} className="p-1.5 bg-blue-100 text-blue-600 rounded-md hover:bg-blue-200 transition-colors">
              <Plus className="w-4 h-4" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {loading ? (
              <div className="flex justify-center p-4"><Loader2 className="w-5 h-5 text-slate-400 animate-spin" /></div>
            ) : files.map((file) => (
              <div 
                key={file.filename}
                onClick={() => setActiveFile(file)}
                className={`group flex items-center justify-between p-3 rounded-lg cursor-pointer transition-all ${activeFile?.filename === file.filename ? 'bg-white shadow-sm border border-slate-200 text-blue-600 font-medium' : 'hover:bg-slate-100 text-slate-600 border border-transparent'}`}
              >
                <div className="flex items-center gap-2 overflow-hidden">
                  <FileText className="w-4 h-4 flex-shrink-0" />
                  <span className="text-sm truncate">{file.filename}</span>
                </div>
                <button 
                  onClick={(e) => { e.stopPropagation(); handleDeleteFile(file.filename); }}
                  className="opacity-0 group-hover:opacity-100 p-1 text-slate-400 hover:text-red-500 transition-all"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
            {files.length === 0 && !loading && (
              <p className="text-xs text-center text-slate-400 p-4">Nenhum documento.</p>
            )}
          </div>
        </div>

        {/* Editor Area */}
        <div className="flex-1 flex flex-col bg-white">
          {activeFile ? (
            <>
              <div className="bg-white px-6 py-4 border-b border-slate-100 flex justify-between items-center">
                <div className="flex items-center gap-2 text-slate-800 font-semibold">
                  <FileText className="w-5 h-5 text-blue-500" />
                  {activeFile.filename}
                </div>
                
                <button 
                  onClick={handleSave}
                  disabled={saving}
                  className="flex items-center gap-2 bg-slate-800 hover:bg-slate-900 disabled:bg-slate-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm"
                >
                  {saving ? (
                    <><Loader2 className="w-4 h-4 animate-spin" /> Salvando...</>
                  ) : success ? (
                    <><CheckCircle2 className="w-4 h-4 text-emerald-400" /> Salvo</>
                  ) : (
                    <><Save className="w-4 h-4" /> Salvar Arquivo</>
                  )}
                </button>
              </div>
              
              <div className="flex-1 p-6 relative bg-slate-50">
                <textarea
                  value={activeFile.content}
                  onChange={(e) => setActiveFile({ ...activeFile, content: e.target.value })}
                  placeholder="Escreva o conteúdo markdown aqui..."
                  className="w-full h-full resize-none outline-none text-slate-700 text-base leading-relaxed bg-transparent font-mono"
                />
              </div>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-slate-400 gap-4 bg-slate-50">
              <FileText className="w-12 h-12 text-slate-200" />
              <p>Selecione ou crie um documento para editar.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

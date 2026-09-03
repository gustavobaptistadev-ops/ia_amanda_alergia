"use client";
import { fetchWithAuth } from '../../lib/api';
import { Database, Save, Loader2, FileText, CheckCircle2, Plus, Trash2, Zap, Building2, CreditCard, Stethoscope, UserCheck, HelpCircle, Sparkles } from "lucide-react";
import { useState, useEffect } from "react";

interface RagFile {
  filename: string;
  content: string;
}

const TEMPLATES = [
  {
    name: "Novo Convênio",
    icon: CreditCard,
    filename: "novo_convenio.md",
    template: `### [Nome do Convênio]
- **Planos Cobertos:** (Ex: Nacional, Executivo, Especial)
- **Cobertura:** Consultas de Alergia, Testes Prick/Patch e Espirometria
- **Regras:** Não exige autorização prévia para consulta básica.
`
  },
  {
    name: "Novo Exame / Preço",
    icon: Stethoscope,
    filename: "novo_exame.md",
    template: `### [Nome do Exame/Procedimento]
- **Indicação:** (Ex: Diagnóstico de asma, alergias alimentares)
- **Preparo:** (Ex: Suspender antialérgicos orais 5 dias antes)
- **Valor Particular:** R$ 0,00
- **Tempo de Resultado:** Imediato / 20 minutos
`
  },
  {
    name: "Novo Médico Especialista",
    icon: UserCheck,
    filename: "novo_medico.md",
    template: `### Dr(a). [Nome do Médico] (CRM-SP [Número] / RQE [Número])
- **Especialidade:** Alergia e Imunologia Clínica
- **Foco de Atendimento:** (Ex: Alergia Pediátrica, Asma Grave)
- **Dias e Horários:** Terças e Quintas (08h às 18h)
`
  },
  {
    name: "Nova Pergunta Frequente (FAQ)",
    icon: HelpCircle,
    filename: "novo_faq.md",
    template: `### Dúvida: [Pergunta do Paciente]
- **Resposta Acolhedora:** [Explicação clara, gentil e sem jargões para a Amanda responder]
`
  }
];

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
        // Auto-indexação inteligente no banco vetorial
        fetchWithAuth(`${apiUrl}/api/v1/rag/train`, { method: "POST" });
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

  const handleApplyTemplate = (tmpl: typeof TEMPLATES[0]) => {
    const filename = prompt(`Nome do arquivo para ${tmpl.name}:`, tmpl.filename);
    if (!filename) return;
    const finalName = filename.endsWith('.md') ? filename : `${filename}.md`;
    const newFile = { filename: finalName, content: tmpl.template };
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

  const getFileIcon = (name: string) => {
    if (name.includes("sobre") || name.includes("clinica")) return Building2;
    if (name.includes("convenio") || name.includes("plano")) return CreditCard;
    if (name.includes("exame") || name.includes("preco")) return Stethoscope;
    if (name.includes("medico") || name.includes("corpo")) return UserCheck;
    return HelpCircle;
  };

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col space-y-6 animate-in fade-in duration-500">
      <div className="flex justify-between items-end">
        <div>
          <h2 className="text-3xl font-bold text-slate-800 flex items-center gap-3">
            <Database className="w-8 h-8 text-blue-600" />
            Base de Conhecimento Enterprise (RAG)
          </h2>
          <p className="text-slate-500 mt-2 max-w-2xl text-sm">
            Gerencie o cérebro institucional da IA Amanda por módulos categorizados. Adicione novos convênios, exames ou médicos com templates guiados.
          </p>
        </div>
        <button 
          onClick={handleTrain}
          disabled={training}
          className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-400 text-white px-6 py-3 rounded-xl font-bold transition-all shadow-md hover:shadow-lg"
        >
          {training ? (
            <><Loader2 className="w-5 h-5 animate-spin" /> Indexando Vetores...</>
          ) : trainSuccess ? (
            <><CheckCircle2 className="w-5 h-5" /> Base 100% Sincronizada!</>
          ) : (
            <><Zap className="w-5 h-5" /> Sincronizar Tudo Agora</>
          )}
        </button>
      </div>

      {/* Barra de Templates Rápidos No-Code */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-100/80 p-4 rounded-2xl flex items-center justify-between">
        <div className="flex items-center gap-2 text-blue-800 font-semibold text-sm">
          <Sparkles className="w-5 h-5 text-blue-600" />
          <span>Templates Rápidos (Inserir sem escrever prompt):</span>
        </div>
        <div className="flex gap-2 flex-wrap">
          {TEMPLATES.map((tmpl) => {
            const Icon = tmpl.icon;
            return (
              <button
                key={tmpl.name}
                onClick={() => handleApplyTemplate(tmpl)}
                className="flex items-center gap-1.5 bg-white hover:bg-blue-600 hover:text-white text-slate-700 border border-slate-200 hover:border-blue-600 px-3 py-1.5 rounded-xl text-xs font-semibold shadow-sm transition-all"
              >
                <Icon className="w-3.5 h-3.5" />
                {tmpl.name}
              </button>
            );
          })}
        </div>
      </div>

      <div className="flex-1 bg-white rounded-2xl shadow-sm border border-slate-100 flex overflow-hidden">
        {/* Sidebar de Arquivos Categorizados */}
        <div className="w-72 border-r border-slate-100 flex flex-col bg-slate-50/50">
          <div className="p-4 border-b border-slate-100 flex justify-between items-center bg-slate-100/50">
            <span className="font-bold text-slate-700 text-sm">Módulos da Clínica</span>
            <span className="text-[11px] bg-blue-100 text-blue-700 font-bold px-2 py-0.5 rounded-full">
              {files.length} {files.length === 1 ? 'doc' : 'docs'}
            </span>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
            {loading ? (
              <div className="flex justify-center p-4"><Loader2 className="w-5 h-5 text-slate-400 animate-spin" /></div>
            ) : files.map((file) => {
              const FileIcon = getFileIcon(file.filename);
              const isSelected = activeFile?.filename === file.filename;
              return (
                <div 
                  key={file.filename}
                  onClick={() => setActiveFile(file)}
                  className={`group flex items-center justify-between p-3 rounded-xl cursor-pointer transition-all ${isSelected ? 'bg-white shadow-sm border border-slate-200 text-blue-600 font-semibold' : 'hover:bg-slate-100 text-slate-600 border border-transparent'}`}
                >
                  <div className="flex items-center gap-2.5 overflow-hidden">
                    <div className={`p-1.5 rounded-lg ${isSelected ? 'bg-blue-50 text-blue-600' : 'bg-slate-100 text-slate-500'}`}>
                      <FileIcon className="w-4 h-4" />
                    </div>
                    <span className="text-xs truncate">{file.filename}</span>
                  </div>
                  <button 
                    onClick={(e) => { e.stopPropagation(); handleDeleteFile(file.filename); }}
                    className="opacity-0 group-hover:opacity-100 p-1 text-slate-400 hover:text-rose-600 transition-all"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })}
          </div>
        </div>

        {/* Editor Area */}
        <div className="flex-1 flex flex-col bg-white">
          {activeFile ? (
            <>
              <div className="bg-white px-6 py-4 border-b border-slate-100 flex justify-between items-center">
                <div className="flex items-center gap-3 text-slate-800 font-bold text-sm">
                  <div className="p-2 bg-blue-50 text-blue-600 rounded-xl">
                    <FileText className="w-4 h-4" />
                  </div>
                  {activeFile.filename}
                </div>
                
                <button 
                  onClick={handleSave}
                  disabled={saving}
                  className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white px-5 py-2.5 rounded-xl text-sm font-semibold transition-all shadow-sm"
                >
                  {saving ? (
                    <><Loader2 className="w-4 h-4 animate-spin" /> Salvando...</>
                  ) : success ? (
                    <><CheckCircle2 className="w-4 h-4 text-emerald-300" /> Salvo & Sincronizado!</>
                  ) : (
                    <><Save className="w-4 h-4" /> Salvar & Indexar</>
                  )}
                </button>
              </div>
              
              <div className="flex-1 p-6 relative bg-slate-50/50">
                <textarea
                  value={activeFile.content}
                  onChange={(e) => setActiveFile({ ...activeFile, content: e.target.value })}
                  placeholder="Escreva as regras do documento aqui..."
                  className="w-full h-full resize-none outline-none text-slate-700 text-sm leading-relaxed bg-transparent font-sans border-0 focus:ring-0"
                />
              </div>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-slate-400 gap-4 bg-slate-50">
              <FileText className="w-12 h-12 text-slate-200" />
              <p className="text-sm font-medium">Selecione ou crie um módulo acima para editar.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

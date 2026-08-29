"use client";
import { fetchWithAuth } from '../../lib/api';

import { QrCode, Smartphone, RefreshCw, Key, CheckCircle2, AlertCircle, Cpu, Sliders, Save, Sparkles, Loader2, ShieldCheck, UserPlus, Lock, ShieldAlert, Users } from "lucide-react";
import { useState, useEffect } from "react";
import Image from "next/image";

interface UserItem {
  id: string;
  name: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export default function Configuracoes() {
  const [activeTab, setActiveTab] = useState<"whatsapp" | "ai" | "credentials">("ai");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [qrCodeBase64, setQrCodeBase64] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // AI Settings State
  const [aiModel, setAiModel] = useState("gpt-4o-mini");
  const [temperature, setTemperature] = useState(0.35);
  const [personaName, setPersonaName] = useState("Amanda");
  const [voiceReplyEnabled, setVoiceReplyEnabled] = useState(false);
  const [voiceName, setVoiceName] = useState("nova");
  const [savingAi, setSavingAi] = useState(false);
  const [aiSuccessMsg, setAiSuccessMsg] = useState(false);

  // Gestão de Credenciais e Usuários
  const [users, setUsers] = useState<UserItem[]>([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [newName, setNewName] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newRole, setNewRole] = useState("recepcionista");
  const [creatingUser, setCreatingUser] = useState(false);
  const [userSuccessMsg, setUserSuccessMsg] = useState("");
  const [userErrorMsg, setUserErrorMsg] = useState("");

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

  const fetchUsers = async () => {
    setLoadingUsers(true);
    try {
      const res = await fetchWithAuth(`${apiUrl}/api/v1/auth/users`);
      if (res.ok) {
        const data = await res.json();
        setUsers(data);
      }
    } catch (e) {
      console.error("Erro ao listar usuários:", e);
    } finally {
      setLoadingUsers(false);
    }
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreatingUser(true);
    setUserSuccessMsg("");
    setUserErrorMsg("");
    try {
      const res = await fetchWithAuth(`${apiUrl}/api/v1/auth/users`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newName,
          email: newEmail,
          password: newPassword,
          role: newRole
        })
      });
      if (res.ok) {
        const data = await res.json();
        setUserSuccessMsg(data.message || "Usuário cadastrado com sucesso!");
        setNewName("");
        setNewEmail("");
        setNewPassword("");
        fetchUsers();
      } else {
        const err = await res.json();
        setUserErrorMsg(err.detail || "Falha ao cadastrar usuário.");
      }
    } catch (err) {
      setUserErrorMsg("Erro de comunicação com o servidor.");
    } finally {
      setCreatingUser(false);
    }
  };

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

  const fetchAiSettings = async () => {
    try {
      const res = await fetchWithAuth(`${apiUrl}/api/v1/settings/`);
      if (res.ok) {
        const data = await res.json();
        if (data.model) setAiModel(data.model);
        if (data.temperature !== undefined) setTemperature(data.temperature);
        if (data.persona_name) setPersonaName(data.persona_name);
        if (data.voice_reply_enabled !== undefined) setVoiceReplyEnabled(data.voice_reply_enabled);
        if (data.voice_name) setVoiceName(data.voice_name);
      }
    } catch (e) {
      console.error("Erro ao carregar configurações de IA:", e);
    }
  };

  const handleSaveAiSettings = async () => {
    setSavingAi(true);
    setAiSuccessMsg(false);
    try {
      const res = await fetchWithAuth(`${apiUrl}/api/v1/settings/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: aiModel,
          temperature: parseFloat(temperature.toString()),
          persona_name: personaName,
          voice_reply_enabled: voiceReplyEnabled,
          voice_name: voiceName
        })
      });
      if (res.ok) {
        setAiSuccessMsg(true);
        setTimeout(() => setAiSuccessMsg(false), 3000);
      } else {
        alert("Erro ao salvar configurações de IA.");
      }
    } catch (e) {
      alert("Falha na comunicação com o servidor.");
    } finally {
      setSavingAi(false);
    }
  };

  const fetchStatusAndQr = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const statusRes = await fetchWithAuth(`${apiUrl}/api/v1/evolution/status`);
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

      const qrRes = await fetchWithAuth(`${apiUrl}/api/v1/evolution/qr`);
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
    fetchAiSettings();
    fetchStatusAndQr();
  }, []);

  return (
    <div className="flex flex-col items-center pt-6 animate-in fade-in duration-500 min-h-screen max-w-4xl mx-auto space-y-6">
      <div className="w-full flex justify-between items-center border-b border-slate-200 pb-4">
        <div>
          <h2 className="text-3xl font-bold text-slate-800">Painel de Configurações</h2>
          <p className="text-slate-500 mt-1 text-sm">Gerencie o modelo cognitivo da IA e as integrações de canais.</p>
        </div>

        {/* Tab Selector */}
        <div className="flex bg-slate-100 p-1 rounded-xl border border-slate-200">
          <button
            onClick={() => setActiveTab("ai")}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold transition-all ${
              activeTab === "ai"
                ? "bg-white text-blue-600 shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <Cpu className="w-4 h-4" />
            Modelo de IA
          </button>
          <button
            onClick={() => setActiveTab("whatsapp")}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold transition-all ${
              activeTab === "whatsapp"
                ? "bg-white text-blue-600 shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <Smartphone className="w-4 h-4" />
            WhatsApp
          </button>
          <button
            onClick={() => { setActiveTab("credentials"); fetchUsers(); }}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold transition-all ${
              activeTab === "credentials"
                ? "bg-white text-blue-600 shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <ShieldCheck className="w-4 h-4" />
            Acessos & Credenciais
          </button>
        </div>
      </div>

      {activeTab === "credentials" ? (
        <div className="w-full space-y-6 animate-in fade-in duration-300">
          {/* Status de Chaves e Segurança */}
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-4">
            <div className="flex items-center gap-3 border-b border-slate-100 pb-4">
              <div className="p-2.5 bg-blue-50 text-blue-600 rounded-xl">
                <Key className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-800">Status das Chaves de Integração (Zero-Trust)</h3>
                <p className="text-xs text-slate-500">Chaves de API ativas e seguras no servidor.</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-slate-700">OpenAI API (GPT-4o Mini / Embeddings)</p>
                  <p className="text-[11px] font-mono text-slate-500">sk-proj-****************</p>
                </div>
                <span className="flex items-center gap-1 text-[11px] font-bold text-emerald-600 bg-emerald-50 px-2 py-1 rounded-md">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Ativo
                </span>
              </div>

              <div className="p-4 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-slate-700">Ghosthub / WhatsApp API</p>
                  <p className="text-[11px] font-mono text-slate-500">sk_live_****************</p>
                </div>
                <span className="flex items-center gap-1 text-[11px] font-bold text-emerald-600 bg-emerald-50 px-2 py-1 rounded-md">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Conectado
                </span>
              </div>

              <div className="p-4 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-slate-700">Google Calendar (Service Account)</p>
                  <p className="text-[11px] font-mono text-slate-500">calendar-sa@respirar.iam...</p>
                </div>
                <span className="flex items-center gap-1 text-[11px] font-bold text-emerald-600 bg-emerald-50 px-2 py-1 rounded-md">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Ativo
                </span>
              </div>

              <div className="p-4 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-slate-700">Webhook Secret Token</p>
                  <p className="text-[11px] font-mono text-slate-500">sk_webhook_************</p>
                </div>
                <span className="flex items-center gap-1 text-[11px] font-bold text-emerald-600 bg-emerald-50 px-2 py-1 rounded-md">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Protegido
                </span>
              </div>
            </div>
          </div>

          {/* Cadastro de Novo Usuário */}
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-4">
            <div className="flex items-center gap-3 border-b border-slate-100 pb-4">
              <div className="p-2.5 bg-indigo-50 text-indigo-600 rounded-xl">
                <UserPlus className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-800">Criar Novo Acesso (Equipe da Clínica)</h3>
                <p className="text-xs text-slate-500">Cadastre médicos e recepcionistas com permissões RBAC.</p>
              </div>
            </div>

            {userSuccessMsg && (
              <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs rounded-xl flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                <span>{userSuccessMsg}</span>
              </div>
            )}

            {userErrorMsg && (
              <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{userErrorMsg}</span>
              </div>
            )}

            <form onSubmit={handleCreateUser} className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">Nome Completo</label>
                <input
                  type="text"
                  required
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="Ex: Dra. Juliana"
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-sm text-slate-800 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">E-mail de Login</label>
                <input
                  type="email"
                  required
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  placeholder="exemplo@respirar.com"
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-sm text-slate-800 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">Senha Inicial</label>
                <input
                  type="password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Mínimo 6 dígitos"
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-sm text-slate-800 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">Perfil de Acesso (RBAC)</label>
                <div className="flex gap-2">
                  <select
                    value={newRole}
                    onChange={(e) => setNewRole(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-sm text-slate-800 focus:outline-none"
                  >
                    <option value="recepcionista">Recepcionista</option>
                    <option value="medico">Médico(a)</option>
                    <option value="admin">Administrador</option>
                  </select>
                  <button
                    type="submit"
                    disabled={creatingUser}
                    className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white px-4 py-2 rounded-xl text-sm font-semibold flex items-center gap-1.5 shadow-sm transition-all flex-shrink-0"
                  >
                    {creatingUser ? <Loader2 className="w-4 h-4 animate-spin" /> : <UserPlus className="w-4 h-4" />}
                    Criar
                  </button>
                </div>
              </div>
            </form>
          </div>

          {/* Tabela de Usuários Cadastrados */}
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-slate-100 text-slate-700 rounded-xl">
                  <Users className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-800">Equipe Cadastrada ({users.length})</h3>
                  <p className="text-xs text-slate-500">Membros com credenciais ativas no painel.</p>
                </div>
              </div>
              <button
                onClick={fetchUsers}
                disabled={loadingUsers}
                className="p-2 text-slate-500 hover:text-slate-800 transition-colors"
                title="Atualizar lista"
              >
                <RefreshCw className={`w-4 h-4 ${loadingUsers ? "animate-spin" : ""}`} />
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-600">
                <thead className="bg-slate-50 text-slate-700 text-xs uppercase font-semibold border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3">Nome</th>
                    <th className="px-4 py-3">E-mail</th>
                    <th className="px-4 py-3">Perfil</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Data de Cadastro</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {users.map((u) => (
                    <tr key={u.id} className="hover:bg-slate-50/60 transition-colors">
                      <td className="px-4 py-3 font-semibold text-slate-800">{u.name}</td>
                      <td className="px-4 py-3 font-mono text-xs">{u.email}</td>
                      <td className="px-4 py-3">
                        <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full ${
                          u.role === 'admin' ? 'bg-purple-100 text-purple-700' :
                          u.role === 'medico' ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-700'
                        }`}>
                          {u.role === 'admin' ? 'Administrador' : u.role === 'medico' ? 'Médico(a)' : 'Recepcionista'}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-[11px] font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">
                          Ativo
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-400">{u.created_at || "Hoje"}</td>
                    </tr>
                  ))}
                  {users.length === 0 && !loadingUsers && (
                    <tr>
                      <td colSpan={5} className="text-center py-6 text-slate-400 text-xs">
                        Nenhum usuário cadastrado.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : activeTab === "ai" ? (
        <div className="w-full bg-white p-8 rounded-2xl shadow-sm border border-slate-200 space-y-8 animate-in fade-in duration-300">
          <div className="flex items-center justify-between border-b border-slate-100 pb-5">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-blue-50 text-blue-600 rounded-xl">
                <Sparkles className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-800">Motor de Inteligência Artificial</h3>
                <p className="text-xs text-slate-500">Escolha o modelo da OpenAI ou ajuste a criatividade das respostas.</p>
              </div>
            </div>

            <button
              onClick={handleSaveAiSettings}
              disabled={savingAi}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white px-6 py-2.5 rounded-xl font-semibold transition-all shadow-sm text-sm"
            >
              {savingAi ? (
                <><Loader2 className="w-4 h-4 animate-spin" /> Salvando...</>
              ) : aiSuccessMsg ? (
                <><CheckCircle2 className="w-4 h-4 text-emerald-300" /> Salvo com Sucesso!</>
              ) : (
                <><Save className="w-4 h-4" /> Salvar Configurações</>
              )}
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Seleção do Modelo */}
            <div className="space-y-3">
              <label className="block text-sm font-semibold text-slate-700">Modelo OpenAI</label>
              <select
                value={aiModel}
                onChange={(e) => setAiModel(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm text-slate-800 font-medium focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-300 transition-all"
              >
                <option value="gpt-4o-mini">GPT-4o Mini (Recomendado - Ultra Rápido & Econômico)</option>
                <option value="gpt-4o">GPT-4o (Máxima Capacidade de Raciocínio & Clínico)</option>
                <option value="gpt-4-turbo">GPT-4 Turbo</option>
                <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
              </select>
              <p className="text-xs text-slate-400">
                O modelo selecionado processará intenções, responderá dúvidas clínicas e acionará a agenda.
              </p>
            </div>

            {/* Nome da Persona */}
            <div className="space-y-3">
              <label className="block text-sm font-semibold text-slate-700">Nome da Assistente (Persona)</label>
              <input
                type="text"
                value={personaName}
                onChange={(e) => setPersonaName(e.target.value)}
                placeholder="Ex: Amanda"
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm text-slate-800 font-medium focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-300 transition-all"
              />
              <p className="text-xs text-slate-400">
                Nome pelo qual a IA se apresentará nas saudações e atendimentos.
              </p>
            </div>

            {/* Temperatura (Criatividade) */}
            <div className="space-y-3 md:col-span-2 bg-slate-50/70 p-6 rounded-2xl border border-slate-100">
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-2">
                  <Sliders className="w-4 h-4 text-slate-500" />
                  <label className="text-sm font-semibold text-slate-700">Temperatura (Criatividade / Foco Clínico)</label>
                </div>
                <span className="font-mono bg-blue-100 text-blue-700 px-3 py-1 rounded-full text-xs font-bold">
                  {temperature}
                </span>
              </div>
              <input
                type="range"
                min="0.0"
                max="1.0"
                step="0.05"
                value={temperature}
                onChange={(e) => setTemperature(parseFloat(e.target.value))}
                className="w-full accent-blue-600 cursor-pointer h-2 bg-slate-200 rounded-lg"
              />
              <div className="flex justify-between text-[11px] text-slate-400 font-medium">
                <span>0.0 (Mais Focada, Precisa e Padronizada)</span>
                <span>1.0 (Mais Criativa e Conversacional)</span>
              </div>
            </div>

            {/* Configuração de Resposta em Áudio Humanizado (TTS) */}
            <div className="space-y-4 md:col-span-2 bg-gradient-to-r from-blue-50/50 to-indigo-50/50 p-6 rounded-2xl border border-blue-100">
              <div className="flex justify-between items-center">
                <div>
                  <h4 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                    🎙️ Respostas em Áudio Humanizado (TTS)
                  </h4>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Quando ativado, caso o paciente envie um áudio, a Amanda responderá com uma mensagem de voz acolhedora.
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={voiceReplyEnabled}
                    onChange={(e) => setVoiceReplyEnabled(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                </label>
              </div>

              {voiceReplyEnabled && (
                <div className="pt-3 border-t border-blue-100/70 grid grid-cols-1 md:grid-cols-2 gap-4 animate-in fade-in">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1.5">Voz da Assistente</label>
                    <select
                      value={voiceName}
                      onChange={(e) => setVoiceName(e.target.value)}
                      className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-sm text-slate-800 font-medium focus:outline-none"
                    >
                      <option value="nova">Nova (Voz Feminina Acolhedora - Recomendada)</option>
                      <option value="shimmer">Shimmer (Voz Feminina Expressiva)</option>
                      <option value="alloy">Alloy (Voz Neutra / Corporativa)</option>
                      <option value="fable">Fable (Voz Dinâmica)</option>
                    </select>
                  </div>
                  <div className="flex items-end">
                    <p className="text-[11px] text-slate-400">
                      Utiliza o motor OpenAI TTS-1 em formato nativo de áudio do WhatsApp (Opus).
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 space-y-6 w-full max-w-md animate-in fade-in duration-300">
          <div className="flex items-center gap-4 border-b border-slate-100 pb-4">
            <div className="p-3 bg-blue-50 rounded-xl">
              <Smartphone className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-slate-800">Conexão WhatsApp</h3>
              <p className="text-sm text-slate-500">Ghosthub / Evolution GO</p>
            </div>
          </div>
          
          <div className="flex flex-col items-center justify-center p-6 bg-slate-50 rounded-xl border-2 border-dashed border-slate-200 min-h-[300px]">
            {success ? (
              <div className="flex flex-col items-center animate-in zoom-in duration-300 w-full">
                <CheckCircle2 className="w-20 h-20 text-emerald-500 mb-4" />
                <p className="text-slate-700 font-medium text-lg">Conectado!</p>
                <p className="text-xs text-slate-400 mt-1 text-center mb-6">A IA já está operando normalmente.</p>
                
                <div className="flex flex-col gap-3 w-full border-t border-slate-200 pt-5">
                  <button
                    onClick={async () => {
                      if (!confirm("Reiniciar a conexão?")) return;
                      setLoading(true);
                      try {
                        await fetchWithAuth(`${apiUrl}/api/v1/evolution/reconnect`, { method: "POST" });
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
                    Reiniciar Sessão
                  </button>
                  
                  <button
                    onClick={async () => {
                      if (!confirm("Desconectar o WhatsApp?")) return;
                      setLoading(true);
                      try {
                        await fetchWithAuth(`${apiUrl}/api/v1/evolution/logout`, { method: "DELETE" });
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
                  onClick={() => fetchStatusAndQr()}
                  disabled={loading}
                  className="flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white w-full py-2.5 rounded-lg font-medium shadow-sm text-sm"
                >
                  <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
                  {loading ? "Carregando..." : "Gerar QR Code"}
                </button>
                <p className="text-[11px] text-slate-500 mt-4 text-center">
                  Vá em Aparelhos Conectados no seu celular para escanear.
                </p>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

"use client";
import { fetchWithAuth } from '../../lib/api';

import { 
  Search, 
  Bot, 
  User, 
  CheckCircle2, 
  Trash2, 
  Calendar, 
  FileText, 
  Phone, 
  ShieldCheck, 
  HeartPulse, 
  Sparkles, 
  Clock, 
  AlertCircle,
  MapPin,
  CreditCard,
  X,
  ChevronLeft,
  Filter,
  Send,
  Mic
} from "lucide-react";
import { useState, useEffect, useRef } from "react";

export default function Conversas() {
  const [contacts, setContacts] = useState<any[]>([]);
  const [selectedContact, setSelectedContact] = useState<any>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [errorMsg, setErrorMsg] = useState("");
  const [inputText, setInputText] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "bot" | "human" | "scheduled">("all");
  const [showPatientDrawer, setShowPatientDrawer] = useState(false); // Fechado por padrão em telas menores
  const [isMobileChatOpen, setIsMobileChatOpen] = useState(false);
  const messagesEndRef = useRef<any>(null);
  const selectedContactRef = useRef<any>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";
  const wsUrl = apiUrl.replace("http", "ws");

  // Fetch initial data
  const fetchContacts = async () => {
    try {
      const res = await fetchWithAuth(`${apiUrl}/api/v1/chats/`);
      if (!res.ok) throw new Error(`Falha ao carregar contatos (${res.status})`);
      const data = await res.json();
      setContacts(data);
      setErrorMsg("");
      // Mantém sincronizado o contato selecionado com dados novos
      if (selectedContact) {
        const updated = data.find((c: any) => c.phone_number === selectedContact.phone_number);
        if (updated) setSelectedContact(updated);
      }
    } catch (e) {
      console.error(e);
      setErrorMsg("Não foi possível carregar as conversas. Tente atualizar a página.");
    }
  };

  const fetchMessages = async (phone: string) => {
    try {
      const res = await fetchWithAuth(`${apiUrl}/api/v1/chats/${phone}/messages`);
      const data = await res.json();
      setMessages(data);
    } catch (e) {
      console.error(e);
    }
  };

  // 1. Efeito de ciclo de vida unico para WebSocket e Polling Global
  useEffect(() => {
    fetchContacts();

    // WebSocket connection com Auto-reconnect e Polling Fallback
    let ws: WebSocket | null = null;
    let reconnectTimeout: any = null;
    let isMounted = true;

    const connectWs = () => {
      try {
        ws = new WebSocket(`${wsUrl}/api/v1/chats/ws`);

        ws.onmessage = (event) => {
          if (event.data === "update") {
            fetchContacts();
            if (selectedContactRef.current) {
              fetchMessages(selectedContactRef.current.phone_number);
            }
          } else if (event.data.startsWith("urgency:")) {
            fetchContacts();
            try {
              const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
              const oscillator = audioCtx.createOscillator();
              oscillator.type = 'sine';
              oscillator.frequency.setValueAtTime(880, audioCtx.currentTime);
              oscillator.connect(audioCtx.destination);
              oscillator.start();
              oscillator.stop(audioCtx.currentTime + 0.4);
            } catch(e) {}
            // Also force UI visual update if needed, but fetchContacts covers it.
          }
        };

        ws.onclose = () => {
          if (isMounted) {
            reconnectTimeout = setTimeout(connectWs, 3000);
          }
        };

        ws.onerror = () => {
          ws?.close();
        };
      } catch (e) {
        if (isMounted) {
          reconnectTimeout = setTimeout(connectWs, 5000);
        }
      }
    };

    connectWs();

    // Polling de fallback seguro a cada 10s
    const interval = setInterval(() => {
      fetchContacts();
      if (selectedContactRef.current) {
        fetchMessages(selectedContactRef.current.phone_number);
      }
    }, 10000);

    return () => {
      isMounted = false;
      clearTimeout(reconnectTimeout);
      clearInterval(interval);
      ws?.close();
    };
  }, []); // Monta apenas uma vez

  // 2. Busca mensagens apenas quando o usuario clicar em um contato diferente
  useEffect(() => {
    selectedContactRef.current = selectedContact;
    if (selectedContact) {
      fetchMessages(selectedContact.phone_number);
    }
  }, [selectedContact?.phone_number]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const toggleBot = async () => {
    if (!selectedContact) return;
    try {
      const res = await fetchWithAuth(`${apiUrl}/api/v1/chats/${selectedContact.phone_number}/toggle_bot`, {
        method: "POST"
      });
      const data = await res.json();
      setSelectedContact({ ...selectedContact, bot_active: data.bot_active });
      fetchContacts();
    } catch (e) {
      console.error(e);
    }
  };

  const sendMessage = async () => {
    if (!inputText.trim() || !selectedContact) return;
    try {
      await fetchWithAuth(`${apiUrl}/api/v1/chats/${selectedContact.phone_number}/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: inputText })
      });
      setInputText("");
      fetchMessages(selectedContact.phone_number);
      fetchContacts();
    } catch (e) {
      console.error(e);
    }
  };

  const resetConversation = async () => {
    if (!selectedContact) return;
    if (window.confirm("Atenção! Isso apagará o histórico de mensagens, resetará o Kanban e limpará a memória da IA para este paciente. Continuar?")) {
      try {
        await fetchWithAuth(`${apiUrl}/api/v1/chats/${selectedContact.phone_number}/reset`, {
          method: "DELETE"
        });
        setMessages([]);
        fetchContacts();
        setSelectedContact({ ...selectedContact, bot_active: true });
      } catch (e) {
        console.error(e);
      }
    }
  };

  const resetAllConversations = async () => {
    if (window.confirm("⚠️ ATENÇÃO MÁXIMA: Deseja apagar TODAS as conversas, contatos e memórias da IA de todo o sistema? Essa ação não pode ser desfeita.")) {
      try {
        const res = await fetchWithAuth(`${apiUrl}/api/v1/chats/reset-all`, {
          method: "DELETE"
        });
        if (res.ok) {
          setMessages([]);
          setSelectedContact(null);
          fetchContacts();
          alert("Todas as conversas foram resetadas com sucesso!");
        }
      } catch (e) {
        console.error(e);
      }
    }
  };

  // Filtragem Reativa de Contatos
  const filteredContacts = contacts.filter((c) => {
    const matchesSearch = 
      (c.name && c.name.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (c.phone_number && c.phone_number.includes(searchTerm)) ||
      (c.insurance_operator && c.insurance_operator.toLowerCase().includes(searchTerm.toLowerCase()));

    if (!matchesSearch) return false;

    if (statusFilter === "bot") return c.bot_active === true;
    if (statusFilter === "human") return c.bot_active === false;
    if (statusFilter === "scheduled") return c.stage === "agendado";
    return true;
  });

  // Renderização amigável de mensagem (com formatação de imagem/carteirinha e áudio transcrito)
  const renderMessageContent = (text: string) => {
    if (text.includes("DADOS EXTRAÍDOS PELA VISÃO COMPUTACIONAL")) {
      const match = text.match(/Operadora: (.*?), Matrícula: (.*?), Plano: (.*?), Acomodação: (.*?), Abrangência: (.*?), Titular: (.*?)]/);
      if (match) {
        return (
          <div className="space-y-2">
            <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-emerald-800 text-xs">
              <div className="flex items-center gap-1.5 font-bold mb-1">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                <span>Carteirinha de Convênio Lida por IA</span>
              </div>
              <p><b>Operadora:</b> {match[1]}</p>
              <p><b>Matrícula:</b> <span className="font-mono">{match[2]}</span></p>
              <p><b>Plano:</b> {match[3]} ({match[4]})</p>
              <p><b>Titular:</b> {match[6]}</p>
            </div>
            <p className="text-sm">{text.split("]. ")[1] || ""}</p>
          </div>
        );
      }
    }

    if (text.startsWith("[Áudio Transcrito por IA]:") || text.includes("Áudio transcrito:")) {
      return (
        <div className="space-y-1.5">
          <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-purple-500/10 border border-purple-500/20 text-purple-700 text-[11px] font-semibold">
            <Mic className="w-3 h-3 text-purple-600 animate-pulse" />
            <span>Áudio Transcrito por IA (Whisper)</span>
          </div>
          <p className="text-sm leading-relaxed whitespace-pre-wrap italic">
            "{text.replace("[Áudio Transcrito por IA]:", "").replace("Áudio transcrito:", "").trim()}"
          </p>
        </div>
      );
    }

    return <p className="text-sm leading-relaxed whitespace-pre-wrap">{text}</p>;
  };

  return (
    <div className="flex-1 flex flex-col space-y-4 animate-in fade-in duration-500 min-h-0 h-[calc(100vh-8rem)] lg:h-full">
      {errorMsg && <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{errorMsg}</div>}
      {/* Header Superior */}
      <div className="flex justify-between items-center pt-14 lg:pt-0">
        <div>
          <h2 className="text-2xl md:text-3xl font-bold text-slate-800">Monitoramento Clínico Omnichannel</h2>
          <p className="text-slate-500 text-xs md:text-sm mt-0.5">Acompanhe as triagens da Amanda IA em tempo real e assuma quando necessário.</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={resetAllConversations}
            title="Apagar todas as mensagens e memórias antigas"
            className="flex items-center gap-1.5 text-xs font-semibold text-rose-600 hover:text-rose-700 bg-rose-50 hover:bg-rose-100 px-3 py-1.5 rounded-full border border-rose-200 transition-all"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Limpar Histórico Geral</span>
          </button>

          <span className="hidden sm:flex items-center gap-1.5 text-xs font-semibold text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded-full border border-emerald-200">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            WhatsApp Ativo
          </span>
        </div>
      </div>

      <div className="flex-1 bg-white rounded-2xl shadow-sm border border-slate-200 flex overflow-hidden relative">
        {/* Coluna 1: Lista de Chats (Responsiva) */}
        <div className={`w-full md:w-80 lg:w-96 border-r border-slate-200 flex flex-col bg-slate-50/50 flex-shrink-0 ${isMobileChatOpen ? 'hidden md:flex' : 'flex'}`}>
          {/* Barra de Busca Reativa */}
          <div className="p-3 border-b border-slate-200 space-y-2">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
              <input 
                type="text" 
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Buscar por nome, fone ou plano..." 
                className="w-full bg-white border border-slate-200 rounded-xl pl-9 pr-4 py-2 text-xs md:text-sm focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-300 transition-all" 
              />
              {searchTerm && (
                <button onClick={() => setSearchTerm("")} className="absolute right-3 top-1/2 transform -translate-y-1/2 text-slate-400 hover:text-slate-600">
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            {/* Pílulas de Filtro Rápido */}
            <div className="flex gap-1.5 overflow-x-auto pb-1 text-[11px] font-semibold text-slate-600 no-scrollbar">
              <button 
                onClick={() => setStatusFilter("all")}
                className={`px-2.5 py-1 rounded-lg transition-colors whitespace-nowrap ${statusFilter === 'all' ? 'bg-blue-600 text-white shadow-xs' : 'bg-white border border-slate-200 hover:bg-slate-100'}`}
              >
                Todos ({contacts.length})
              </button>
              <button 
                onClick={() => setStatusFilter("bot")}
                className={`px-2.5 py-1 rounded-lg transition-colors whitespace-nowrap flex items-center gap-1 ${statusFilter === 'bot' ? 'bg-blue-600 text-white shadow-xs' : 'bg-white border border-slate-200 hover:bg-slate-100'}`}
              >
                <Bot className="w-3 h-3" /> IA Amanda
              </button>
              <button 
                onClick={() => setStatusFilter("human")}
                className={`px-2.5 py-1 rounded-lg transition-colors whitespace-nowrap flex items-center gap-1 ${statusFilter === 'human' ? 'bg-amber-600 text-white shadow-xs' : 'bg-white border border-slate-200 hover:bg-slate-100'}`}
              >
                <User className="w-3 h-3" /> Humano
              </button>
              <button 
                onClick={() => setStatusFilter("scheduled")}
                className={`px-2.5 py-1 rounded-lg transition-colors whitespace-nowrap flex items-center gap-1 ${statusFilter === 'scheduled' ? 'bg-emerald-600 text-white shadow-xs' : 'bg-white border border-slate-200 hover:bg-slate-100'}`}
              >
                <Calendar className="w-3 h-3" /> Agendados
              </button>
            </div>
          </div>

          {/* Lista de Contatos */}
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {filteredContacts.map((contact) => (
              <div 
                key={contact.id} 
                onClick={() => {
                  setSelectedContact(contact);
                  setIsMobileChatOpen(true);
                }}
                className={`p-3 rounded-xl flex items-center gap-3 cursor-pointer transition-all ${selectedContact?.id === contact.id ? 'bg-white shadow-sm border border-blue-200' : 'hover:bg-slate-100/70 border border-transparent'}`}>
                <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm flex-shrink-0 ${contact.bot_active ? 'bg-blue-100 text-blue-600' : 'bg-amber-100 text-amber-600'}`}>
                  {contact.name ? contact.name.substring(0, 2).toUpperCase() : '??'}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-baseline">
                    <h4 className="font-semibold text-slate-800 text-sm truncate">{contact.name || contact.phone_number}</h4>
                  </div>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${contact.bot_active ? "bg-blue-50 text-blue-600" : "bg-amber-50 text-amber-700"}`}>
                      {contact.bot_active ? "IA Amanda" : "Humano"}
                    </span>
                    {contact.insurance_operator && (
                      <span className="text-[10px] bg-emerald-50 text-emerald-700 font-semibold px-1.5 py-0.5 rounded truncate">
                        {contact.insurance_operator}
                      </span>
                    )}
                    <span className="text-[11px] text-slate-400 truncate">
                      {contact.stage ? contact.stage.replace('_', ' ') : 'Novo'}
                    </span>
                  </div>
                </div>
              </div>
            ))}
            {filteredContacts.length === 0 && (
              <div className="p-8 text-center text-xs text-slate-400">Nenhum paciente encontrado com esses filtros.</div>
            )}
          </div>
        </div>

        {/* Coluna 2: Área Central da Conversa */}
        <div className={`flex-1 flex-col bg-slate-50 min-w-0 ${isMobileChatOpen ? 'flex' : 'hidden md:flex'}`}>
          {selectedContact ? (
            <>
              {/* Header do Chat */}
              <div className="p-3 md:p-4 px-4 md:px-6 border-b border-slate-200 bg-white flex items-center justify-between gap-2 overflow-x-auto no-scrollbar">
                <div className="flex items-center gap-2 md:gap-3 flex-1 min-w-0 pr-2 shrink-0">
                  <button 
                    onClick={() => setIsMobileChatOpen(false)}
                    className="md:hidden p-1.5 text-slate-500 hover:text-slate-800 rounded-lg hover:bg-slate-100"
                  >
                    <ChevronLeft className="w-5 h-5" />
                  </button>
                  <div className={`w-3 h-3 rounded-full flex-shrink-0 ${!selectedContact.bot_active ? "bg-amber-500" : "bg-emerald-500"}`}></div>
                  <div className="min-w-0">
                    <h3 className="font-bold text-slate-800 text-sm md:text-base truncate">{selectedContact.name || selectedContact.phone_number}</h3>
                    <p className="text-[11px] text-slate-400 flex items-center gap-2 truncate">
                      <span>{selectedContact.phone_number}</span>
                      <span>•</span>
                      <span>{!selectedContact.bot_active ? "Atendente Manual" : "IA Amanda Ativa"}</span>
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={resetConversation}
                    title="Resetar conversa e apagar memória"
                    className="text-xs font-medium text-slate-400 hover:text-rose-600 bg-slate-50 hover:bg-rose-50 p-2 rounded-xl border border-slate-200 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>

                  <button
                    onClick={() => setShowPatientDrawer(!showPatientDrawer)}
                    title="Alternar Ficha Clínica"
                    className={`text-xs font-medium px-3 py-2 rounded-xl border transition-colors flex items-center gap-1.5 ${showPatientDrawer ? 'bg-blue-50 text-blue-600 border-blue-200' : 'bg-slate-50 text-slate-600 border-slate-200'}`}
                  >
                    <FileText className="w-4 h-4" />
                    <span className="hidden sm:inline">Ficha Clínica</span>
                  </button>

                  {selectedContact.bot_active ? (
                    <button 
                      onClick={toggleBot}
                      className="text-xs font-semibold text-rose-600 bg-rose-50 hover:bg-rose-100 border border-rose-200 px-3 py-2 rounded-xl transition-all"
                    >
                      Assumir
                    </button>
                  ) : (
                    <button 
                      onClick={toggleBot}
                      className="text-xs font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 px-3 py-2 rounded-xl transition-all flex items-center gap-1.5"
                    >
                      <CheckCircle2 className="w-4 h-4" />
                      <span className="hidden sm:inline">Devolver IA</span>
                    </button>
                  )}
                </div>
              </div>
              
              {/* Balões de Mensagem */}
              <div className="flex-1 p-4 md:p-6 overflow-y-auto space-y-4">
                {messages.map((msg) => (
                  <div key={msg.id} className={`flex ${msg.sender === 'paciente' ? 'justify-start' : 'justify-end'}`}>
                    <div className={`p-4 rounded-2xl max-w-[85%] md:max-w-[75%] shadow-sm ${msg.sender === 'paciente' ? 'bg-white border border-slate-200 rounded-tl-sm' : msg.sender === 'ia' ? 'bg-blue-600 text-white rounded-tr-sm' : 'bg-amber-600 text-white rounded-tr-sm'}`}>
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-[10px] font-bold uppercase tracking-wider ${msg.sender === 'paciente' ? 'text-slate-400' : 'text-blue-200'}`}>
                          {msg.sender === 'paciente' ? 'Paciente' : msg.sender === 'ia' ? 'Amanda (IA)' : 'Atendente'}
                        </span>
                      </div>
                      <div className={msg.sender === 'paciente' ? 'text-slate-800' : 'text-white'}>
                        {renderMessageContent(msg.text)}
                      </div>
                      <span className={`text-[10px] mt-1.5 block ${msg.sender === 'paciente' ? 'text-slate-400' : 'text-white/70 text-right'}`}>
                        {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>

              {/* Barra de Respostas Rápidas da Recepção */}
              {!selectedContact.bot_active && (
                <div className="px-4 py-2 bg-slate-100/70 border-t border-slate-200 flex gap-2 overflow-x-auto text-[11px]">
                  <span className="text-slate-400 font-semibold flex items-center py-1">Atalhos:</span>
                  <button 
                    onClick={() => setInputText("Endereço da Clínica Lifeline One: Connect Towers, sala 3021 - QS 01, Rua 212, Lotes 19, 21 e 23 - Taguatinga Sul, Brasília - DF. Como chegar pelo Waze: https://ul.waze.com/ul?ll=-15.84028486%2C-48.04482222&navigate=yes&zoom=17&utm_campaign=default&utm_source=waze_website&utm_medium=lm_share_location")}
                    className="bg-white hover:bg-blue-50 hover:text-blue-600 text-slate-700 px-2.5 py-1 rounded-lg border border-slate-200 transition-colors whitespace-nowrap flex items-center gap-1 font-medium"
                  >
                    <MapPin className="w-3 h-3 text-blue-500" /> Endereço & Rota
                  </button>
                  <button 
                    onClick={() => setInputText("🧪 Preparo para o Teste de Alergia: Para garantir a precisão do exame, suspender antialérgicos orais (anti-histamínicos) de 5 a 7 dias antes do atendimento.")}
                    className="bg-white hover:bg-blue-50 hover:text-blue-600 text-slate-700 px-2.5 py-1 rounded-lg border border-slate-200 transition-colors whitespace-nowrap flex items-center gap-1 font-medium"
                  >
                    <FileText className="w-3 h-3 text-purple-500" /> Preparo de Exames
                  </button>
                  <button 
                    onClick={() => setInputText("Segue nossa chave PIX oficial (CNPJ): 12.345.678/0001-90 - Clínica Lifeline One Medicina e Imunologia Ltda.")}
                    className="bg-white hover:bg-blue-50 hover:text-blue-600 text-slate-700 px-2.5 py-1 rounded-lg border border-slate-200 transition-colors whitespace-nowrap flex items-center gap-1 font-medium"
                  >
                    <CreditCard className="w-3 h-3 text-emerald-500" /> Dados PIX
                  </button>
                </div>
              )}
              
              {/* Input de Envio de Mensagem */}
              <div className="p-3 md:p-4 bg-white border-t border-slate-200">
                {!selectedContact.bot_active ? (
                  <div className="relative flex items-center">
                    <input 
                      type="text" 
                      value={inputText}
                      onChange={(e) => setInputText(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
                      placeholder={`Digite sua resposta manual para ${selectedContact.name || selectedContact.phone_number}...`} 
                      className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-4 pr-12 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-300 transition-all" 
                    />
                    <button onClick={sendMessage} className="absolute right-2.5 bg-blue-600 hover:bg-blue-700 text-white p-2 rounded-lg transition-colors">
                      <Send className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <div className="bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-xs text-slate-500 text-center flex items-center justify-center gap-2">
                    <Bot className="w-4 h-4 text-blue-600 flex-shrink-0" /> <span>Amanda IA está atendendo este paciente. Clique em <b>"Assumir"</b> para responder manualmente.</span>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-slate-400 flex-col gap-3 p-6">
              <Search className="w-12 h-12 text-slate-300" />
              <p className="text-sm font-medium">Selecione uma conversa para monitorar a triagem clínica.</p>
            </div>
          )}
        </div>

        {/* Coluna 3: Ficha Rápida do Paciente (Drawer Responsivo Slide-Over) */}
        {selectedContact && showPatientDrawer && (
          <div className="fixed inset-y-0 right-0 z-50 w-80 md:w-88 bg-white shadow-2xl md:shadow-none md:static md:border-l md:border-slate-200 p-6 flex flex-col space-y-6 overflow-y-auto animate-in slide-in-from-right duration-300">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center font-bold text-base border border-blue-100">
                  {selectedContact.name ? selectedContact.name.substring(0, 2).toUpperCase() : 'PT'}
                </div>
                <div className="min-w-0">
                  <h3 className="font-bold text-slate-800 text-sm truncate">{selectedContact.name || "Paciente"}</h3>
                  <p className="text-xs text-slate-400 font-mono truncate">{selectedContact.phone_number}</p>
                </div>
              </div>
              <button 
                onClick={() => setShowPatientDrawer(false)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Informações de Convênio & Carteirinha Lida por IA */}
            <div className="space-y-3">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-slate-500" /> Plano de Saúde & Carteirinha
              </h4>
              <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-100 space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-500">Operadora:</span>
                  <span className="font-semibold text-slate-800">
                    {selectedContact.insurance_operator || "Particular / Não informada"}
                  </span>
                </div>
                {selectedContact.insurance_card_number && (
                  <div className="flex justify-between">
                    <span className="text-slate-500">Matrícula:</span>
                    <span className="font-mono font-semibold text-slate-800">
                      {selectedContact.insurance_card_number}
                    </span>
                  </div>
                )}
                {selectedContact.insurance_plan_name && (
                  <div className="flex justify-between">
                    <span className="text-slate-500">Plano / Categoria:</span>
                    <span className="font-medium text-slate-700">
                      {selectedContact.insurance_plan_name}
                    </span>
                  </div>
                )}
                {selectedContact.insurance_accommodation && (
                  <div className="flex justify-between">
                    <span className="text-slate-500">Acomodação:</span>
                    <span className="font-medium text-slate-700">
                      {selectedContact.insurance_accommodation}
                    </span>
                  </div>
                )}
                <div className="flex justify-between pt-1 border-t border-slate-200/60">
                  <span className="text-slate-500">Etapa do Funil:</span>
                  <span className="font-semibold text-blue-600 capitalize">
                    {selectedContact.stage ? selectedContact.stage.replace('_', ' ') : 'Triagem'}
                  </span>
                </div>
              </div>
            </div>

            {/* Resumo da Queixa / Sintomas Identificados pela IA */}
            <div className="space-y-3">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <HeartPulse className="w-4 h-4 text-rose-500" /> Resumo Clínico (Amanda IA)
              </h4>
              <div className="bg-rose-50/50 p-3.5 rounded-xl border border-rose-100 text-xs text-slate-700 leading-relaxed">
                <p className="font-medium text-slate-800 mb-1">Queixas Triadas:</p>
                "Paciente buscou atendimento para teste de alergia respiratória e esclareceu regras de cobertura de exames com a Amanda."
              </div>
            </div>

            {/* Ações Rápidas da Recepção */}
            <div className="space-y-2 pt-2 border-t border-slate-100">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Ações Rápidas</h4>
              <button
                onClick={() => {
                  setInputText("Olá! Seguem as orientações e preparo para sua consulta e exames na Clínica Lifeline One: 1. Chegar com 10 min de antecedência; 2. Trazer documento com foto.");
                  setShowPatientDrawer(false);
                }}
                className="w-full text-left text-xs bg-slate-50 hover:bg-blue-50 text-slate-700 hover:text-blue-700 p-2.5 rounded-xl border border-slate-200 transition-colors font-medium flex items-center gap-2"
              >
                <FileText className="w-3.5 h-3.5 text-blue-600" /> Enviar Preparo de Exames
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

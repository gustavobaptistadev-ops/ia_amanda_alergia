"use client";
import { fetchWithAuth } from '../../lib/api';

import { Search, Bot, User, CheckCircle2, Trash2, Calendar, FileText, Phone, ShieldCheck, HeartPulse, Sparkles, Clock, AlertCircle } from "lucide-react";
import { useState, useEffect, useRef } from "react";

export default function Conversas() {
  const [contacts, setContacts] = useState<any[]>([]);
  const [selectedContact, setSelectedContact] = useState<any>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [inputText, setInputText] = useState("");
  const [showPatientDrawer, setShowPatientDrawer] = useState(true);
  const messagesEndRef = useRef<any>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";
  const wsUrl = apiUrl.replace("http", "ws");

  // Fetch initial data
  const fetchContacts = async () => {
    try {
      const res = await fetchWithAuth(`${apiUrl}/api/v1/chats/`);
      const data = await res.json();
      setContacts(data);
    } catch (e) {
      console.error(e);
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
            if (selectedContact) {
              fetchMessages(selectedContact.phone_number);
            }
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

    // Polling de fallback caso o WebSocket falhe
    const interval = setInterval(() => {
      fetchContacts();
      if (selectedContact) {
        fetchMessages(selectedContact.phone_number);
      }
    }, 8000);

    return () => {
      isMounted = false;
      clearTimeout(reconnectTimeout);
      clearInterval(interval);
      ws?.close();
    };
  }, [selectedContact]);

  useEffect(() => {
    if (selectedContact) {
      fetchMessages(selectedContact.phone_number);
    }
  }, [selectedContact]);

  useEffect(() => {
    // Scroll to bottom
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
    } catch (e) {
      console.error(e);
    }
  };

  const resetConversation = async () => {
    if (!selectedContact) return;
    if (window.confirm("Atenção! Isso apagará TODO o histórico de mensagens, resetará o Kanban para Novo Contato e limpará a memória da IA para este número. Continuar?")) {
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

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col space-y-6 animate-in fade-in duration-500">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-3xl font-bold text-slate-800">Monitoramento Clínico Omnichannel</h2>
          <p className="text-slate-500 mt-1">Acompanhe as triagens da Amanda IA em tempo real e assuma quando necessário.</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5 text-xs font-semibold text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded-full border border-emerald-200">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            Canal WhatsApp Conectado
          </span>
        </div>
      </div>

      <div className="flex-1 bg-white rounded-2xl shadow-sm border border-slate-200 flex overflow-hidden">
        {/* Coluna 1: Lista de Chats */}
        <div className="w-80 border-r border-slate-200 flex flex-col bg-slate-50/50 flex-shrink-0">
          <div className="p-4 border-b border-slate-200">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
              <input type="text" placeholder="Buscar paciente..." className="w-full bg-white border border-slate-200 rounded-full pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-300 transition-all" />
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {contacts.map((contact) => (
              <div 
                key={contact.id} 
                onClick={() => setSelectedContact(contact)}
                className={`p-3.5 rounded-xl flex items-center gap-3 cursor-pointer transition-all ${selectedContact?.id === contact.id ? 'bg-white shadow-sm border border-slate-200' : 'hover:bg-slate-100/70 border border-transparent'}`}>
                <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm flex-shrink-0 ${contact.bot_active ? 'bg-blue-100 text-blue-600' : 'bg-amber-100 text-amber-600'}`}>
                  {contact.name ? contact.name.substring(0, 2).toUpperCase() : '??'}
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="font-semibold text-slate-800 text-sm truncate">{contact.name || contact.phone_number}</h4>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${contact.bot_active ? "bg-blue-50 text-blue-600" : "bg-amber-50 text-amber-700"}`}>
                      {contact.bot_active ? "IA Amanda" : "Humano"}
                    </span>
                    <span className="text-[11px] text-slate-400 truncate">
                      {contact.stage ? contact.stage.replace('_', ' ') : 'Novo'}
                    </span>
                  </div>
                </div>
              </div>
            ))}
            {contacts.length === 0 && (
              <div className="p-6 text-center text-sm text-slate-400">Nenhuma conversa encontrada.</div>
            )}
          </div>
        </div>

        {/* Coluna 2: Área Central da Conversa */}
        <div className="flex-1 flex flex-col bg-slate-50 min-w-0">
          {selectedContact ? (
            <>
              <div className="p-4 px-6 border-b border-slate-200 bg-white flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-3 h-3 rounded-full ${!selectedContact.bot_active ? "bg-amber-500" : "bg-emerald-500"}`}></div>
                  <div>
                    <h3 className="font-bold text-slate-800 text-base">{selectedContact.name || selectedContact.phone_number}</h3>
                    <p className="text-xs text-slate-400 flex items-center gap-2">
                      <span>{selectedContact.phone_number}</span>
                      <span>•</span>
                      <span>{!selectedContact.bot_active ? "Atendimento Manual (Operador)" : "Em Atendimento com Amanda IA"}</span>
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
                    <FileText className="w-4 h-4" /> Ficha Clínica
                  </button>

                  {selectedContact.bot_active ? (
                    <button 
                      onClick={toggleBot}
                      className="text-xs font-semibold text-rose-600 bg-rose-50 hover:bg-rose-100 border border-rose-200 px-3.5 py-2 rounded-xl transition-all"
                    >
                      Assumir
                    </button>
                  ) : (
                    <button 
                      onClick={toggleBot}
                      className="text-xs font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 px-3.5 py-2 rounded-xl transition-all flex items-center gap-1.5"
                    >
                      <CheckCircle2 className="w-4 h-4" /> Devolver IA
                    </button>
                  )}
                </div>
              </div>
              
              <div className="flex-1 p-6 overflow-y-auto space-y-4">
                {messages.map((msg) => (
                  <div key={msg.id} className={`flex ${msg.sender === 'paciente' ? 'justify-start' : 'justify-end'}`}>
                    <div className={`p-4 rounded-2xl max-w-[80%] shadow-sm ${msg.sender === 'paciente' ? 'bg-white border border-slate-200 rounded-tl-sm' : msg.sender === 'ia' ? 'bg-blue-600 text-white rounded-tr-sm' : 'bg-amber-600 text-white rounded-tr-sm'}`}>
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-[10px] font-bold uppercase tracking-wider ${msg.sender === 'paciente' ? 'text-slate-400' : 'text-blue-200'}`}>
                          {msg.sender === 'paciente' ? 'Paciente' : msg.sender === 'ia' ? 'Amanda (IA)' : 'Atendente'}
                        </span>
                      </div>
                      <p className={`text-sm leading-relaxed ${msg.sender === 'paciente' ? 'text-slate-800' : 'text-white'}`}>{msg.text}</p>
                      <span className={`text-[10px] mt-1.5 block ${msg.sender === 'paciente' ? 'text-slate-400' : 'text-white/70 text-right'}`}>
                        {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>
              
              <div className="p-4 bg-white border-t border-slate-200">
                {!selectedContact.bot_active ? (
                  <div className="relative">
                    <input 
                      type="text" 
                      value={inputText}
                      onChange={(e) => setInputText(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
                      placeholder={`Digite sua resposta manual para ${selectedContact.name || selectedContact.phone_number}...`} 
                      className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-4 pr-12 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-300 transition-all" 
                    />
                    <button onClick={sendMessage} className="absolute right-2.5 top-1/2 transform -translate-y-1/2 bg-blue-600 hover:bg-blue-700 text-white p-2 rounded-lg">
                      <User className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <div className="bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-xs text-slate-500 text-center flex items-center justify-center gap-2">
                    <Bot className="w-4 h-4 text-blue-600" /> Amanda IA está atendendo este paciente. Clique em <b>"Assumir"</b> para responder manualmente.
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-slate-400 flex-col gap-3">
              <Search className="w-10 h-10 text-slate-300" />
              <p className="text-sm">Selecione uma conversa para monitorar a triagem clínica.</p>
            </div>
          )}
        </div>

        {/* Coluna 3: Ficha Rápida do Paciente (Enterprise Drawer) */}
        {selectedContact && showPatientDrawer && (
          <div className="w-80 border-l border-slate-200 bg-white p-6 flex flex-col space-y-6 overflow-y-auto flex-shrink-0 animate-in slide-in-from-right duration-300">
            <div className="flex items-center gap-3 border-b border-slate-100 pb-4">
              <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center font-bold text-lg border border-blue-100">
                {selectedContact.name ? selectedContact.name.substring(0, 2).toUpperCase() : 'PT'}
              </div>
              <div>
                <h3 className="font-bold text-slate-800 text-base">{selectedContact.name || "Paciente"}</h3>
                <p className="text-xs text-slate-400 font-mono">{selectedContact.phone_number}</p>
              </div>
            </div>

            {/* Informações de Convênio & Cadastro */}
            <div className="space-y-3">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-slate-500" /> Dados Cadastrais (LGPD)
              </h4>
              <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-100 space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-500">Convênio:</span>
                  <span className="font-semibold text-slate-800">Unimed / Particular</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Etapa do Funil:</span>
                  <span className="font-semibold text-blue-600 capitalize">
                    {selectedContact.stage ? selectedContact.stage.replace('_', ' ') : 'Triagem'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Origem:</span>
                  <span className="font-semibold text-slate-800">WhatsApp Direto</span>
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
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Ações da Recepção</h4>
              <button
                onClick={() => {
                  setInputText("Olá! Seguem as orientações e preparo para sua consulta e exames na Clínica Respirar: 1. Chegar com 10 min de antecedência; 2. Trazer documento com foto.");
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

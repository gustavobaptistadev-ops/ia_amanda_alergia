"use client";
import { fetchWithAuth } from '../../lib/api';

import { Search, Bot, User, CheckCircle2, Trash2 } from "lucide-react";
import { useState, useEffect, useRef } from "react";

export default function Conversas() {
  const [contacts, setContacts] = useState<any[]>([]);
  const [selectedContact, setSelectedContact] = useState<any>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [inputText, setInputText] = useState("");
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
      // Message will be fetched via websocket update
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
        setSelectedContact({ ...selectedContact, bot_active: true }); // Assume that backend reset sets bot_active = True
      } catch (e) {
        console.error(e);
      }
    }
  };

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col space-y-6 animate-in fade-in duration-500">
      <div>
        <h2 className="text-3xl font-bold text-slate-800">Monitoramento Ao Vivo</h2>
        <p className="text-slate-500 mt-1">Acompanhe as conversas reais da IA e assuma o controle quando precisar.</p>
      </div>

      <div className="flex-1 bg-white rounded-2xl shadow-sm border border-slate-100 flex overflow-hidden">
        {/* Lista de Chats */}
        <div className="w-1/3 border-r border-slate-100 flex flex-col bg-slate-50/50">
          <div className="p-4 border-b border-slate-100">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
              <input type="text" placeholder="Buscar paciente..." className="w-full bg-white border border-slate-200 rounded-full pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-300 transition-all" />
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            {contacts.map((contact) => (
              <div 
                key={contact.id} 
                onClick={() => setSelectedContact(contact)}
                className={`p-4 rounded-xl flex items-center gap-4 cursor-pointer transition-all ${selectedContact?.id === contact.id ? 'bg-white shadow-sm border border-slate-100' : 'hover:bg-slate-100/50 border border-transparent'}`}>
                <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm ${contact.bot_active ? 'bg-blue-100 text-blue-600' : 'bg-amber-100 text-amber-600'}`}>
                  {contact.name ? contact.name.substring(0, 2).toUpperCase() : '??'}
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="font-semibold text-slate-800 truncate">{contact.name || contact.phone_number}</h4>
                  <p className="text-xs text-slate-500 truncate">{contact.bot_active ? "IA Ativa" : "Atendimento Humano"}</p>
                </div>
              </div>
            ))}
            {contacts.length === 0 && (
              <div className="p-4 text-center text-sm text-slate-500">Nenhuma conversa encontrada.</div>
            )}
          </div>
        </div>

        {/* Área da Conversa */}
        <div className="flex-1 flex flex-col bg-slate-50">
          {selectedContact ? (
            <>
              <div className="p-6 border-b border-slate-100 bg-white flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-slate-800 text-lg">{selectedContact.name || selectedContact.phone_number}</h3>
                  <p className={`text-xs font-medium flex items-center gap-1 ${!selectedContact.bot_active ? "text-amber-500" : "text-emerald-500"}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${!selectedContact.bot_active ? "bg-amber-500" : "bg-emerald-500"}`}></span>
                    {!selectedContact.bot_active ? "Atendimento Manual (Você)" : "Sendo atendido pela IA"}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={resetConversation}
                    title="Resetar conversa e apagar memória"
                    className="text-sm font-medium text-slate-400 bg-slate-50 px-3 py-2 rounded-full hover:bg-slate-100 hover:text-red-500 transition-colors flex items-center justify-center"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                  {selectedContact.bot_active && (
                    <button 
                      onClick={toggleBot}
                      className="text-sm font-medium text-rose-600 bg-rose-50 px-4 py-2 rounded-full hover:bg-rose-100 transition-colors"
                    >
                      Assumir Atendimento
                    </button>
                  )}
                  {!selectedContact.bot_active && (
                    <button 
                      onClick={toggleBot}
                      className="text-sm font-medium text-emerald-600 bg-emerald-50 px-4 py-2 rounded-full hover:bg-emerald-100 transition-colors flex items-center gap-1"
                    >
                      <CheckCircle2 className="w-4 h-4" /> Devolver para IA
                    </button>
                  )}
                </div>
              </div>
              
              <div className="flex-1 p-6 overflow-y-auto space-y-6">
                {messages.map((msg) => (
                  <div key={msg.id} className={`flex ${msg.sender === 'paciente' ? 'justify-start' : 'justify-end'}`}>
                    <div className={`p-4 rounded-2xl max-w-[80%] shadow-sm ${msg.sender === 'paciente' ? 'bg-white border border-slate-100 rounded-tl-sm' : msg.sender === 'ia' ? 'bg-blue-600 text-white rounded-tr-sm' : 'bg-amber-500 text-white rounded-tr-sm'}`}>
                      <p className={msg.sender === 'paciente' ? 'text-slate-700' : 'text-white'}>{msg.text}</p>
                      <span className={`text-[10px] mt-2 block ${msg.sender === 'paciente' ? 'text-slate-400' : 'text-white/70 text-right'}`}>
                        {new Date(msg.created_at).toLocaleTimeString()} {msg.sender === 'humano' ? '(Você)' : ''}
                      </span>
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>
              
              <div className="p-4 bg-white border-t border-slate-100">
                {!selectedContact.bot_active ? (
                  <div className="relative">
                    <input 
                      type="text" 
                      value={inputText}
                      onChange={(e) => setInputText(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
                      placeholder={`Digite sua mensagem para ${selectedContact.name || selectedContact.phone_number}...`} 
                      className="w-full bg-slate-50 border border-slate-200 rounded-full pl-6 pr-12 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-300 transition-all" 
                    />
                    <button onClick={sendMessage} className="absolute right-3 top-1/2 transform -translate-y-1/2 bg-blue-600 text-white p-1.5 rounded-full hover:bg-blue-700">
                      <User className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <div className="bg-slate-50 border border-slate-200 rounded-full px-4 py-3 text-sm text-slate-400 text-center flex items-center justify-center gap-2">
                    <Bot className="w-4 h-4" /> Você está no modo espectador. A IA está conduzindo esta conversa.
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-slate-400 flex-col gap-4">
              <Search className="w-12 h-12 text-slate-200" />
              <p>Selecione uma conversa ao lado para monitorar</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

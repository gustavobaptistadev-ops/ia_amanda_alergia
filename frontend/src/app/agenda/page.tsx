"use client";
import { fetchWithAuth } from '../../lib/api';

import { 
  Calendar as CalendarIcon, 
  Clock, 
  User, 
  Phone, 
  CheckCircle2, 
  XCircle, 
  AlertCircle, 
  Plus, 
  Edit3, 
  Trash2, 
  RefreshCw, 
  Search, 
  Filter, 
  ChevronLeft, 
  ChevronRight,
  Loader2,
  CalendarCheck,
  FileText
} from "lucide-react";
import { useState, useEffect } from "react";

interface Appointment {
  id: string;
  contact_id: string;
  patient_name: string;
  phone_number: string;
  appointment_time: string;
  status: string;
  created_at: string;
}

export default function Agenda() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("todos");
  
  // Modal de Edição / Criação
  const [showModal, setShowModal] = useState(false);
  const [editingAppt, setEditingAppt] = useState<Appointment | null>(null);
  const [patientName, setPatientName] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [appointmentDate, setAppointmentDate] = useState("");
  const [appointmentTime, setAppointmentTime] = useState("10:00");
  const [status, setStatus] = useState("agendado");
  const [saving, setSaving] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

  const fetchAppointments = async () => {
    setLoading(true);
    try {
      const res = await fetchWithAuth(`${apiUrl}/api/v1/appointments/`);
      if (res.ok) {
        const data = await res.json();
        setAppointments(data);
      }
    } catch (e) {
      console.error("Erro ao buscar agenda:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAppointments();
    const interval = setInterval(fetchAppointments, 15000); // Polling de 15s
    return () => clearInterval(interval);
  }, []);

  const handleOpenCreate = () => {
    setEditingAppt(null);
    setPatientName("");
    setPhoneNumber("55");
    const today = new Date().toISOString().split("T")[0];
    setAppointmentDate(today);
    setAppointmentTime("10:00");
    setStatus("agendado");
    setErrorMsg("");
    setShowModal(true);
  };

  const handleOpenEdit = (appt: Appointment) => {
    setEditingAppt(appt);
    setPatientName(appt.patient_name);
    setPhoneNumber(appt.phone_number);
    const dt = new Date(appt.appointment_time);
    setAppointmentDate(dt.toISOString().split("T")[0]);
    const hours = String(dt.getHours()).padStart(2, '0');
    const minutes = String(dt.getMinutes()).padStart(2, '0');
    setAppointmentTime(`${hours}:${minutes}`);
    setStatus(appt.status);
    setErrorMsg("");
    setShowModal(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setErrorMsg("");

    try {
      const fullDateTime = `${appointmentDate}T${appointmentTime}:00`;

      if (editingAppt) {
        // Atualizar
        const res = await fetchWithAuth(`${apiUrl}/api/v1/appointments/${editingAppt.id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            patient_name: patientName,
            appointment_time: fullDateTime,
            status: status
          })
        });

        if (res.ok) {
          setShowModal(false);
          fetchAppointments();
        } else {
          const err = await res.json();
          setErrorMsg(err.detail || "Erro ao atualizar consulta.");
        }
      } else {
        // Criar Novo
        const res = await fetchWithAuth(`${apiUrl}/api/v1/appointments/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            patient_name: patientName,
            phone_number: phoneNumber,
            appointment_time: fullDateTime,
            status: status
          })
        });

        if (res.ok) {
          setShowModal(false);
          fetchAppointments();
        } else {
          const err = await res.json();
          setErrorMsg(err.detail || "Erro ao criar consulta.");
        }
      }
    } catch (err) {
      setErrorMsg("Erro de comunicação com o servidor.");
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = async (id: string) => {
    if (!window.confirm("Deseja realmente desmarcar/cancelar esta consulta?")) return;
    try {
      const res = await fetchWithAuth(`${apiUrl}/api/v1/appointments/${id}`, {
        method: "DELETE"
      });
      if (res.ok) {
        fetchAppointments();
      }
    } catch (e) {
      alert("Erro ao cancelar consulta.");
    }
  };

  const filteredAppointments = appointments.filter((appt) => {
    const matchesSearch = appt.patient_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          appt.phone_number.includes(searchTerm);
    const matchesStatus = statusFilter === "todos" || appt.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const handleExportCSV = () => {
    if (appointments.length === 0) {
      alert("Nenhuma consulta para exportar.");
      return;
    }
    const headers = ["Data", "Horario", "Paciente", "Telefone", "Status"];
    const rows = appointments.map((appt) => {
      const dt = new Date(appt.appointment_time);
      const dateStr = dt.toLocaleDateString("pt-BR");
      const timeStr = dt.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
      return [
        `"${dateStr}"`,
        `"${timeStr}"`,
        `"${appt.patient_name.replace(/"/g, '""')}"`,
        `"${appt.phone_number}"`,
        `"${appt.status}"`
      ].join(",");
    });
    const csvContent = "data:text/csv;charset=utf-8,\uFEFF" + [headers.join(","), ...rows].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `agenda_consultas_${new Date().toISOString().split("T")[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500 min-h-screen">
      {/* Header Superior da Agenda */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h2 className="text-3xl font-bold text-slate-800 flex items-center gap-3">
            <CalendarIcon className="w-8 h-8 text-blue-600" /> Agenda Médica em Tempo Real
          </h2>
          <p className="text-slate-500 mt-1 text-sm">
            Visualização e gestão ao vivo de todas as consultas agendadas pela Amanda IA e recepção.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleExportCSV}
            className="flex items-center gap-2 bg-slate-100 hover:bg-slate-200 text-slate-700 px-4 py-2.5 rounded-xl font-semibold text-sm transition-all"
            title="Exportar consultas em formato CSV"
          >
            <FileText className="w-4 h-4 text-emerald-600" /> Exportar Planilha (CSV)
          </button>

          <button
            onClick={fetchAppointments}
            disabled={loading}
            className="p-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl transition-colors"
            title="Atualizar Agenda"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>

          <button
            onClick={handleOpenCreate}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl font-semibold text-sm shadow-sm transition-all"
          >
            <Plus className="w-4 h-4" /> Nova Consulta Manual
          </button>
        </div>
      </div>

      {/* Barra de Filtros e Busca */}
      <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-200 flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Buscar por paciente ou telefone..."
            className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-100"
          />
        </div>

        <div className="flex items-center gap-2 w-full md:w-auto">
          <Filter className="w-4 h-4 text-slate-400" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs font-semibold text-slate-700 focus:outline-none"
          >
            <option value="todos">Todos os Status</option>
            <option value="agendado">Agendados</option>
            <option value="confirmado">Confirmados</option>
            <option value="concluido">Concluídos</option>
            <option value="cancelado">Cancelados</option>
          </select>
        </div>
      </div>

      {/* Lista de Consultas / Grade */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-600">
            <thead className="bg-slate-50 text-slate-700 text-xs uppercase font-semibold border-b border-slate-200">
              <tr>
                <th className="px-6 py-4">Data & Horário</th>
                <th className="px-6 py-4">Paciente</th>
                <th className="px-6 py-4">Telefone (WhatsApp)</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4 text-right">Ações em Tempo Real</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredAppointments.map((appt) => {
                const dateObj = new Date(appt.appointment_time);
                const formattedDate = dateObj.toLocaleDateString("pt-BR", { weekday: 'short', day: '2-digit', month: '2-digit', year: 'numeric' });
                const formattedTime = dateObj.toLocaleTimeString("pt-BR", { hour: '2-digit', minute: '2-digit' });

                return (
                  <tr key={appt.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div className="p-2 bg-blue-50 text-blue-600 rounded-lg">
                          <Clock className="w-4 h-4" />
                        </div>
                        <div>
                          <p className="font-bold text-slate-800 text-sm">{formattedTime}</p>
                          <p className="text-xs text-slate-400 capitalize">{formattedDate}</p>
                        </div>
                      </div>
                    </td>

                    <td className="px-6 py-4 font-semibold text-slate-800">
                      {appt.patient_name}
                    </td>

                    <td className="px-6 py-4 font-mono text-xs text-slate-500">
                      {appt.phone_number}
                    </td>

                    <td className="px-6 py-4">
                      <span className={`text-xs font-bold px-3 py-1 rounded-full ${
                        appt.status === 'confirmado' ? 'bg-emerald-100 text-emerald-700' :
                        appt.status === 'agendado' ? 'bg-blue-100 text-blue-700' :
                        appt.status === 'concluido' ? 'bg-purple-100 text-purple-700' :
                        'bg-rose-100 text-rose-700'
                      }`}>
                        {appt.status === 'confirmado' ? 'Confirmado' :
                         appt.status === 'agendado' ? 'Agendado' :
                         appt.status === 'concluido' ? 'Concluído' : 'Cancelado'}
                      </span>
                    </td>

                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleOpenEdit(appt)}
                          className="p-2 text-slate-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                          title="Editar Consulta / Horário"
                        >
                          <Edit3 className="w-4 h-4" />
                        </button>

                        {appt.status !== 'cancelado' && (
                          <button
                            onClick={() => handleCancel(appt.id)}
                            className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                            title="Desmarcar / Cancelar"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}

              {filteredAppointments.length === 0 && !loading && (
                <tr>
                  <td colSpan={5} className="text-center py-12 text-slate-400 text-sm">
                    <CalendarCheck className="w-12 h-12 mx-auto text-slate-300 mb-3" />
                    Nenhuma consulta encontrada na agenda.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal de Criação / Edição de Consulta */}
      {showModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in">
          <div className="bg-white rounded-3xl p-8 max-w-lg w-full shadow-2xl border border-slate-100 space-y-6">
            <div className="flex justify-between items-center border-b border-slate-100 pb-4">
              <h3 className="text-lg font-bold text-slate-800">
                {editingAppt ? "Editar Agendamento Médico" : "Novo Agendamento Manual"}
              </h3>
              <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-slate-600">
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            {errorMsg && (
              <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            <form onSubmit={handleSave} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Nome Completo do Paciente</label>
                <input
                  type="text"
                  required
                  value={patientName}
                  onChange={(e) => setPatientName(e.target.value)}
                  placeholder="Ex: Maria Silva"
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-100"
                />
              </div>

              {!editingAppt && (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Telefone WhatsApp (com DDI/DDD)</label>
                  <input
                    type="text"
                    required
                    value={phoneNumber}
                    onChange={(e) => setPhoneNumber(e.target.value)}
                    placeholder="Ex: 5561999999999"
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-100 font-mono"
                  />
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Data da Consulta</label>
                  <input
                    type="date"
                    required
                    value={appointmentDate}
                    onChange={(e) => setAppointmentDate(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-800 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Horário</label>
                  <input
                    type="time"
                    required
                    value={appointmentTime}
                    onChange={(e) => setAppointmentTime(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-800 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Status do Agendamento</label>
                <select
                  value={status}
                  onChange={(e) => setStatus(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-800 focus:outline-none"
                >
                  <option value="agendado">Agendado</option>
                  <option value="confirmado">Confirmado</option>
                  <option value="concluido">Concluído / Atendido</option>
                  <option value="cancelado">Cancelado</option>
                </select>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-5 py-2.5 text-slate-600 hover:bg-slate-100 rounded-xl text-sm font-semibold transition-all"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white px-6 py-2.5 rounded-xl text-sm font-semibold shadow-sm transition-all"
                >
                  {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                  Salvar Consulta
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

import React from 'react';
import { Calendar, dateFnsLocalizer, Views } from 'react-big-calendar';
import { format, parse, startOfWeek, getDay } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import 'react-big-calendar/lib/css/react-big-calendar.css';
import './calendar-overrides.css';

const locales = {
  'pt-BR': ptBR,
};

const localizer = dateFnsLocalizer({
  format,
  parse,
  startOfWeek,
  getDay,
  locales,
});

interface Appointment {
  id: string;
  contact_id: string;
  patient_name: string;
  phone_number: string;
  appointment_time: string;
  status: string;
  created_at: string;
}

interface CalendarViewProps {
  appointments: Appointment[];
  onSelectEvent: (appt: Appointment) => void;
}

export default function CalendarView({ appointments, onSelectEvent }: CalendarViewProps) {
  // Converter os Appointments para o formato de eventos do react-big-calendar
  const events = appointments.map(appt => {
    const start = new Date(appt.appointment_time);
    const end = new Date(start.getTime() + 60 * 60 * 1000); // +1 hora

    return {
      title: `${appt.patient_name} - ${appt.status}`,
      start,
      end,
      resource: appt,
    };
  });

  return (
    <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-200 h-[700px] w-full">
      <Calendar
        localizer={localizer}
        events={events}
        startAccessor="start"
        endAccessor="end"
        culture="pt-BR"
        messages={{
          next: "Próximo",
          previous: "Anterior",
          today: "Hoje",
          month: "Mês",
          week: "Semana",
          day: "Dia",
          agenda: "Agenda",
          date: "Data",
          time: "Hora",
          event: "Evento",
          noEventsInRange: "Não há consultas neste período."
        }}
        defaultView={Views.WEEK}
        views={[Views.MONTH, Views.WEEK, Views.DAY]}
        step={30}
        timeslots={2}
        min={new Date(2024, 0, 1, 7, 0, 0)} // Inicia às 07:00
        max={new Date(2024, 0, 1, 20, 0, 0)} // Termina às 20:00
        onSelectEvent={(event: any) => onSelectEvent(event.resource)}
        eventPropGetter={(event) => {
          let backgroundColor = '#2563eb'; // blue-600 (Agendado)
          if (event.resource.status === 'cancelado') backgroundColor = '#ef4444'; // red-500
          if (event.resource.status === 'concluido') backgroundColor = '#10b981'; // emerald-500
          
          return {
            style: {
              backgroundColor,
              borderRadius: '6px',
              opacity: 0.9,
              color: 'white',
              border: '0px',
              display: 'block',
              fontWeight: 500,
              fontSize: '0.875rem',
              padding: '2px 6px',
            }
          };
        }}
      />
    </div>
  );
}

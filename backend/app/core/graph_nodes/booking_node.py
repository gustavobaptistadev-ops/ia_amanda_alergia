import datetime
import re
from app.core.state import AgentState
from app.core.booking_state import validate_booking_state, mark_booking_created, set_offered_slots
from app.core.conversation_router import extract_requested_date
from app.core.rag import retrieve_context
from app.services.google_calendar import check_availability, create_event

async def schedule_flow_node(state: AgentState):
    """Consulta disponibilidade automaticamente quando os dados permitem agendamento."""
    """Nó 2b: Fluxo dedicado para agendamento com corpo clínico e regras."""
    last_message = state["messages"][-1].content
    intent = state.get("intent", "")
    routing = state.get("routing", {})
    booking = state.get("booking", {})
    existing_context = state.get("context", "")

    if "[TRIAGEM CLÍNICA]" in existing_context:
        return {"context": existing_context}

    record_validation = validate_booking_state(booking) if booking else {}
    if intent == "AGENDAMENTO" and not booking.get("complaint_collected"):
        # Não consulta RAG nem agenda antes de conhecer o motivo da consulta.
        return {"context": ""}

    if intent == "AGENDAMENTO" and routing.get("next_action") == "REVIEW_PATIENT_DATA":
        return {
            "context": "[REVISAO_DADOS_PRONTUARIO] Existem dados conflitantes ou inválidos. Solicitar correção sem expor valores internos."
        }

    if (
        intent == "AGENDAMENTO"
        and routing.get("next_action") == "CONFIRM_SLOT"
        and not record_validation.get("valid")
    ):
        return {
            "context": "[REVISAO_DADOS_PRONTUARIO] A ficha não passou na validação administrativa. Não executar ferramentas."
        }

    if intent == "AGENDAMENTO" and routing.get("next_action") == "CONFIRM_SLOT":
        slot = booking.get("selected_slot") or {}
        patient_name = booking.get("patient_name") or ""
        cpf = booking.get("cpf") or ""
        dob = booking.get("birth_date") or ""
        if slot.get("date") and slot.get("time") and patient_name and cpf and dob:
            booking_result = await create_event.ainvoke(
                {
                    "date_str": slot["date"],
                    "time_str": slot["time"],
                    "patient_name": patient_name,
                    "cpf": cpf,
                    "dob": dob,
                    "phone": state.get("thread_id", ""),
                    "email": booking.get("email", ""),
                    "clinical_summary": booking.get("clinical_summary", ""),
                    "payment_type": booking.get("payment_type", ""),
                    "insurance_operator": booking.get("insurance_operator", ""),
                    "insurance_card": booking.get("insurance_card", ""),
                }
            )
            booking_succeeded = any(
                term in str(booking_result).lower()
                for term in ("confirmado", "registrado", "sucesso")
            )
            updated_booking = booking
            if booking_succeeded:
                appointment_match = re.search(
                    r"/calendar/p/([0-9a-f-]{36})", str(booking_result), re.IGNORECASE
                )
                updated_booking = mark_booking_created(
                    booking,
                    appointment_match.group(1) if appointment_match else None,
                )
            return {
                "context": (
                    "[AGENDAMENTO_EXECUTADO]\\n"
                    f"Resultado interno da criacao: {booking_result}"
                ),
                "booking": updated_booking,
            }

    context = retrieve_context(f"{last_message} médicos convênios preços")
    if (
        intent == "AGENDAMENTO"
        and routing.get("next_action") == "CHECK_AVAILABILITY"
        and record_validation.get("valid")
    ):
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3)))
        if now.hour < 8 or now.hour >= 18:
            return {
                "context": "[FORA_DO_EXPEDIENTE] A triagem foi concluída, mas estamos fora do horário comercial (08h às 18h). Não apresente horários. Avise que a equipe retornará amanhã de manhã. Se houver queixa de dor intensa ou urgência na triagem, sugira procurar o pronto-socorro mais próximo.",
                "booking": booking,
            }

        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3)))
        requested_date = booking.get("requested_date") or extract_requested_date(
            last_message, now.date()
        )
        if requested_date:
            target_dates = [requested_date]
        else:
            target_dates = []
            target_date = now.date() + datetime.timedelta(days=1)
            while len(target_dates) < 2:
                if target_date.weekday() != 6:
                    target_dates.append(target_date.isoformat())
                target_date += datetime.timedelta(days=1)

        agenda_lines = []
        offered_slots = []
        for target_date_str in target_dates:
            agenda_result = await check_availability.ainvoke(
                {"date_str": target_date_str, "period": "todos"}
            )
            times = re.findall(r"\\b\\d{1,2}:\\d{2}\\b", agenda_result or "")
            if times:
                date_obj = datetime.date.fromisoformat(target_date_str)
                weekday_names = (
                    "Segunda-feira",
                    "Terça-feira",
                    "Quarta-feira",
                    "Quinta-feira",
                    "Sexta-feira",
                    "Sábado",
                    "Domingo",
                )
                agenda_lines.append(
                    f"{weekday_names[date_obj.weekday()]}, {date_obj.strftime('%d/%m/%Y')}: "
                    f"{', '.join(times[:3])}"
                )
                offered_slots.extend(
                    {"date": target_date_str, "time": time_value}
                    for time_value in times[:3]
                )
        formatted_agenda = "\\n".join(agenda_lines)
        booking = set_offered_slots(booking, offered_slots)
        context += (
            "\\n\\n[AGENDA CONSULTADA AUTOMATICAMENTE]\\n"
            f"[AGENDA_RESULTADO]\\n{formatted_agenda}\\n[FIM_AGENDA_RESULTADO]"
        )
        context += "\\n[APENAS_APRESENTAR_HORARIOS]"

    return {"context": context, "booking": booking}

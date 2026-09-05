from app.core.state import AgentState

async def clinical_triage_node(state: AgentState):
    """Nó Triage: Avalia sintomas e direciona para perguntas empáticas de anamnese com inteligência RAG."""
    from app.core.rag import retrieve_context

    patient_profile = state.get("patient_profile", {})
    symptoms = patient_profile.get("symptoms")
    symptoms_duration = patient_profile.get("symptoms_duration")
    medications = patient_profile.get("medications", [])

    context = ""
    # Only triage if symptoms were mentioned but duration/medications are missing
    if symptoms and (not symptoms_duration or not medications):
        # Busca o protocolo de triagem equivalente ao sintoma usando o motor semântico
        query = f"Protocolos de Triagem Clínica - Alergia e Imunologia. Sintomas relatados: {symptoms}"
        rag_protocol = retrieve_context(query)

        context = (
            f"[TRIAGEM CLÍNICA] O paciente relatou o seguinte sintoma: '{symptoms}'.\\n\\n"
            "Aja como uma recepcionista clínica especialista da Lifeline One.\\n"
            "MUITO IMPORTANTE: Baseie sua próxima pergunta **estritamente** nas DIRETRIZES DE PERGUNTA do protocolo médico abaixo, focando na investigação empática do fator desencadeante.\\n\\n"
            f"--- PROTOCOLO MÉDICO DE REFERÊNCIA ---\\n{rag_protocol}\\n--------------------------------------\\n\\n"
        )
        if not symptoms_duration:
            context += "Instrução adicional: Pergunte também, de forma muito sutil, há quanto tempo ele está com esses sintomas.\\n"
        elif not medications:
            context += "Instrução adicional: Pergunte também se ele tomou algum medicamento para aliviar esse quadro.\\n"

        context += "Lembre-se: Faça apenas UMA pergunta por vez, com extrema empatia e compaixão, e NÃO dê diagnósticos."

    return {"context": context}

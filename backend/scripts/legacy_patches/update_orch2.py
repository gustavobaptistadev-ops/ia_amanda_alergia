import re

with open('backend/app/core/orchestrator.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add Date Normalization
if 'RELÓGIO DO SISTEMA' not in content:
    date_context = '''    # [CONSCIÊNCIA TEMPORAL DINÂMICA & CALENDÁRIO CANÔNICO ANTI-ALUCINAÇÃO]
    now_sp = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3)))
    
    # NEW: Date normalization for prompt
    dias_semana = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
    dia_str = dias_semana[now_sp.weekday()]
    data_str = now_sp.strftime("%d/%m/%Y")
    hora_str = now_sp.strftime("%H:%M")
    
    temporal_anchor = f"\\n\\n[RELÓGIO DO SISTEMA]\\nHoje é {dia_str}, {data_str}. A hora atual é {hora_str}. Use esta data como referencial absoluto para interpretar 'amanhã', 'próxima semana', etc.\\n"
    
    hora = now_sp.hour'''
    
    content = re.sub(r'    # \[CONSCIÊNCIA TEMPORAL.*?hora = now_sp.hour', date_context, content, flags=re.DOTALL)

    # STRICT ONBOARDING
    onboarding = '''                if profile_parts:
                    patient_profile_str = "📄 FICHA PRÉVIA DO PACIENTE (MEMÓRIA DE LONGO PRAZO):\\n" + "\\n".join(profile_parts) + "\\n\\n"
                    
                # STRICT ONBOARDING LOGIC
                if not active_contact.name or not active_contact.stage == "agendado":
                    # If we don't have basic data, force intent to novo_paciente so prompt_master applies strict rules
                    if intent in ["AGENDAMENTO", "duvidas_clinica", "fetch_context"]:
                        intent = "novo_paciente"
                        contact_status_str += "\\n[ALERTA DE SISTEMA]: O paciente AINDA NÃO TEM CADASTRO COMPLETO. Você não pode prosseguir com agendamento nem pesquisar horários. Você DEVE coletar o NOME COMPLETO e CPF do paciente nesta exata mensagem. Faça isso de forma educada.\\n"
'''
    content = content.replace('                if profile_parts:\\n                    patient_profile_str = "📄 FICHA PRÉVIA DO PACIENTE (MEMÓRIA DE LONGO PRAZO):\\n" + "\\n".join(profile_parts) + "\\n\\n"', onboarding)

with open('backend/app/core/orchestrator.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("done")

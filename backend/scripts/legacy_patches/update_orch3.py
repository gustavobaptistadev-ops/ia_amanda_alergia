import re

with open('backend/app/core/orchestrator.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Instead of replacing the string, I'll insert after profile_parts check
if 'STRICT ONBOARDING LOGIC' not in content:
    target = 'patient_profile_str = '
    # find where patient_profile_str is assigned
    # Actually, let's just insert before 'if is_initial_turn and patient_name:'
    target = 'if is_initial_turn and patient_name:'
    onboarding = '''
                # STRICT ONBOARDING LOGIC
                if not active_contact.name or not active_contact.stage == "agendado":
                    # If we don't have basic data, force intent to novo_paciente so prompt_master applies strict rules
                    if intent in ["AGENDAMENTO", "duvidas_clinica", "fetch_context"]:
                        intent = "novo_paciente"
                        contact_status_str += "\\n[ALERTA DE SISTEMA]: O paciente AINDA NÃO TEM CADASTRO COMPLETO. Você não pode prosseguir com agendamento nem pesquisar horários. Você DEVE coletar o NOME COMPLETO e CPF do paciente nesta exata mensagem. Faça isso de forma educada.\\n"
                
                '''
    content = content.replace(target, onboarding + target)

with open('backend/app/core/orchestrator.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("done")

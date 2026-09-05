import re

with open('backend/app/core/orchestrator.py', 'r', encoding='utf-8') as f:
    content = f.read()

date_logic = '''    # [CONSCIÊNCIA TEMPORAL E CALENDÁRIO ABSOLUTO]
    now_sp = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3)))
    dias_semana = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
    dia_str = dias_semana[now_sp.weekday()]
    data_str = now_sp.strftime("%d/%m/%Y")
    hora_str = now_sp.strftime("%H:%M")
    temporal_anchor = f"\\n[RELÓGIO DO SISTEMA]\\nHoje é {dia_str}, {data_str}. A hora atual é {hora_str}. Use esta data como referencial para interpretar amanhã e próxima semana.\\n"
'''

content = content.replace('    hoje = datetime.date.today().strftime("%d/%m/%Y")', date_logic)

onboarding_logic = '''
            if active_contact:
                # [STRICT ONBOARDING] Se faltar dados vitais e for pra agendar/dúvida, force o onboarding
                if (not active_contact.name or not active_contact.stage == "agendado"):
                    if intent in ["AGENDAMENTO", "duvidas_clinica", "fetch_context"]:
                        intent = "novo_paciente"
                        contact_status_str += "\\n[ALERTA DE SISTEMA]: O PACIENTE AINDA NÃO TEM CADASTRO COMPLETO. Você não pode prosseguir com agendamento nem pesquisar horários! Você DEVE coletar o NOME COMPLETO e CPF do paciente de forma educada ANTES de prosseguir.\\n"
'''
content = content.replace('            if active_contact:\\n                profile_parts = []', onboarding_logic + '\\n                profile_parts = []')

with open('backend/app/core/orchestrator.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("done")

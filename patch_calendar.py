import re

with open('backend/app/services/google_calendar.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix location in google cal link
content = content.replace(
    'details_param = urllib.parse.quote("Consulta Médica na Clínica Respirar.\\nAv. Paulista, 1000 - Cj 1204.")',
    'details_param = urllib.parse.quote("Consulta Médica na Clínica Respirar.\\nConnect Towers, sala 3021 - QS 01, Taguatinga Sul.")'
)

content = content.replace(
    'location_param = urllib.parse.quote("Av. Paulista, 1000, Bela Vista, São Paulo")',
    'location_param = urllib.parse.quote("Connect Towers, QS 01 Rua 212, Taguatinga, Brasília, DF")'
)

# Fix location in ICS file
content = content.replace(
    'f"DESCRIPTION:Consulta Médica na Clínica Respirar.\\\\nAv. Paulista\\\\, 1000 - Cj 1204.",',
    'f"DESCRIPTION:Consulta Médica na Clínica Respirar.\\\\nConnect Towers\\\\, sala 3021 - QS 01\\\\, Taguatinga Sul.",'
)

content = content.replace(
    'f"LOCATION:Av. Paulista\\\\, 1000\\\\, Bela Vista\\\\, São Paulo",',
    'f"LOCATION:Connect Towers\\\\, QS 01 Rua 212\\\\, Taguatinga\\\\, Brasília\\\\, DF",'
)

# Add link_info to the return for when API is unavailable (service=None)
content = content.replace(
    '''f"2. O arquivo de convite (.ics) já foi enviado automaticamente pelo sistema! Apenas diga: 'Já enviei o arquivo de convite logo abaixo para você salvar na sua agenda com 1 toque!'\\n"''',
    '''f"2. O arquivo de convite (.ics) já foi disparado, MAS VOCÊ TAMBÉM DEVE INCLUIR ESTE LINK NA MENSAGEM: {google_cal_link}\\n"'''
)

# Add link_info to the return for when API is available (success block)
content = content.replace(
    '''f"2. O arquivo de convite (.ics) já foi disparado! Apenas avise: 'Já enviei o convite logo abaixo para você salvar na sua agenda do celular com 1 clique!'\\n"''',
    '''f"2. O arquivo de convite (.ics) já foi disparado, MAS VOCÊ TAMBÉM DEVE INCLUIR O LINK NA MENSAGEM! Diga algo como: 'Para salvar na agenda, basta clicar no convite abaixo ou neste link: {google_cal_link}'\\n"'''
)

with open('backend/app/services/google_calendar.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("done")

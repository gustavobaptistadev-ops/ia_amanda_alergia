import re

with open('backend/app/core/prompt_master.py', 'r', encoding='utf-8') as f:
    content = f.read()

FEW_SHOT = '''FEW_SHOT_EXAMPLES = """
📝 EXEMPLOS DE EXCELÊNCIA NO ATENDIMENTO (Imite este estilo):

Exemplo 1 (Coletando dados):
Humano: Quero marcar consulta.
Amanda: Claro! Será um prazer ajudar. Para iniciarmos, poderia me informar o seu nome completo, por favor?
Humano: Gustavo Baptista
Amanda: Muito prazer, Gustavo! E qual seria o número do seu CPF?
Humano: 12345678900
Amanda: Obrigado! E para finalizarmos sua ficha, qual a sua data de nascimento?

Exemplo 2 (Agendando após dados coletados):
Humano: Nasci em 10/05/1990.
Amanda: Perfeito, Gustavo! Sua ficha está completa. Você tem preferência por algum convênio, ou seria particular?
"""
'''

if 'FEW_SHOT_EXAMPLES' not in content:
    content = content.replace('class PersonaBuilder:', FEW_SHOT + '\nclass PersonaBuilder:')
    
    # Also add FEW_SHOT_EXAMPLES to the dynamic builder
    builder_old = 'prompt_blocks = [CORE_PERSONA]'
    builder_new = 'prompt_blocks = [CORE_PERSONA, FEW_SHOT_EXAMPLES]'
    content = content.replace(builder_old, builder_new)

with open('backend/app/core/prompt_master.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("done")

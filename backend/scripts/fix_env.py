import os
from cryptography.fernet import Fernet
import secrets

filepath = r"d:\GUSTAVO\NOVOS PROJETOS\ia_amanda\sistema_recepção_inteligente\backend\.env"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("generate-a-unique-random-secret-at-least-32-characters", secrets.token_hex(16))
content = content.replace("generate-another-unique-random-secret-at-least-32-characters", secrets.token_hex(16))
content = content.replace("generate-a-third-unique-random-secret-at-least-32-characters", secrets.token_hex(16))
content = content.replace("generate-and-manage-a-fernet-key-in-your-secret-manager", Fernet.generate_key().decode('utf-8'))

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Env file updated with valid secrets.")

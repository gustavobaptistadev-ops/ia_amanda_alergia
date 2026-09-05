import os
import secrets
from cryptography.fernet import Fernet

filepath = r"d:\GUSTAVO\NOVOS PROJETOS\ia_amanda\sistema_recepção_inteligente\backend\.env"

with open(filepath, "a", encoding="utf-8") as f:
    f.write(f"\nINTERNAL_API_KEY={secrets.token_hex(16)}\n")
    f.write(f"WEBHOOK_SECRET={secrets.token_hex(16)}\n")
    f.write(f"JWT_SECRET_KEY={secrets.token_hex(16)}\n")
    f.write(f"ENCRYPTION_KEY={Fernet.generate_key().decode('utf-8')}\n")

print("Env file appended.")

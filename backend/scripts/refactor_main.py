import re

filepath = r"d:\GUSTAVO\NOVOS PROJETOS\ia_amanda\sistema_recepção_inteligente\backend\app\main.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Substituir bloco do DDL e do RAG por um bloco menor
pattern = r"# 1\. Garante que tabelas novas \(system_logs, users, etc\) sejam criadas.*?# Auto-create the instance in Evolution GO using the Global Key"

replacement = """# 1. Garante que tabelas novas sejam criadas (usar alembic para colunas)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Tabelas sincronizadas no PostgreSQL com sucesso.")
    
    # Ingestão de RAG foi movida para o script standalone `backend/scripts/seed_rag.py`
    
    # Auto-create the instance in Evolution GO using the Global Key"""

content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Refatoração do main.py aplicada com sucesso.")

import re

with open('backend/app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = 'logger.info("Tabelas e colunas sincronizadas no PostgreSQL com sucesso.")'

replacement = '''logger.info("Tabelas e colunas sincronizadas no PostgreSQL com sucesso.")
    
    # Ingestão de RAG no startup se existir OPENAI_API_KEY
    import os, glob
    from app.core.rag import ingest_docs
    if os.getenv("OPENAI_API_KEY"):
        logger.info("Iniciando ingestão da base de conhecimento (RAG)...")
        kb_dir = os.path.join(os.path.dirname(__file__), '../docs/knowledge_base')
        try:
            for file in glob.glob(os.path.join(kb_dir, '*.md')):
                ingest_docs(file)
            logger.info("Ingestão de RAG concluída no startup.")
        except Exception as e:
            logger.error(f"Erro na ingestão de RAG: {e}")'''

content = content.replace(target, replacement)

with open('backend/app/main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("done")

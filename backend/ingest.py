import os
from dotenv import load_dotenv

# Carregar variáveis do .env antes de importar os módulos que as usam
load_dotenv()

from app.core.rag import ingest_docs

if __name__ == "__main__":
    doc_path = os.path.join(os.path.dirname(__file__), "docs", "clinica_alergia_contexto.md")
    print(f"Iniciando ingestão do arquivo: {doc_path}")
    ingest_docs(doc_path)
    print("Processo finalizado!")

"""Script utilitário standalone para popular/atualizar a base de conhecimento (RAG) no ChromaDB."""

import os
import glob
import logging
import sys
from dotenv import load_dotenv

# Carrega as variáveis de ambiente antes de importar módulos do app
load_dotenv()

# Ajusta o sys.path para permitir importações absolutas de 'app'
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.core.rag import ingest_docs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("Aviso: OPENAI_API_KEY não definida. Abortando ingestão de RAG.")
        return

    logger.info("Iniciando ingestão da base de conhecimento (RAG)...")
    kb_dir = os.path.join(os.path.dirname(__file__), '../docs/knowledge_base')
    
    md_files = glob.glob(os.path.join(kb_dir, '*.md'))
    if not md_files:
        logger.warning(f"Nenhum arquivo markdown encontrado em: {kb_dir}")
        return

    for file_path in md_files:
        try:
            ingest_docs(file_path)
            logger.info(f"Arquivo {os.path.basename(file_path)} ingerido com sucesso.")
        except Exception as e:
            logger.error(f"Erro na ingestão de RAG do arquivo {file_path}: {e}")
            
    logger.info("Ingestão de RAG concluída.")

if __name__ == "__main__":
    main()

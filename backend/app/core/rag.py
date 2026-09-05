import logging
import os

from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores.pgvector import PGVector
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.config import settings

logger = logging.getLogger(__name__)

# Configurações do Banco. O langchain community usa psycopg2.
# Substituímos asyncpg caso exista na string.
db_url = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ia_amanda"
)
if "+asyncpg" in db_url:
    db_url = db_url.replace("+asyncpg", "")

collection_name = "clinica_docs"


def get_embeddings():
    api_key = settings.OPENAI_API_KEY
    return OpenAIEmbeddings(openai_api_key=api_key)


def get_vectorstore() -> PGVector:
    return PGVector(
        collection_name=collection_name,
        connection_string=db_url,
        embedding_function=get_embeddings(),
    )


def ingest_docs(file_path: str):
    """Lê um documento e o insere no banco de vetores."""
    logger.info(f"Lendo documento: {file_path}")
    loader = TextLoader(file_path, encoding="utf-8")
    documents = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs = text_splitter.split_documents(documents)

    logger.info(f"Ingerindo {len(docs)} fragmentos (chunks) no PostgreSQL (pgvector)...")

    # Previne duplicidade limpando a coleção antes de inserir os novos
    store = get_vectorstore()
    store.delete_collection()

    PGVector.from_documents(
        embedding=get_embeddings(),
        documents=docs,
        collection_name=collection_name,
        connection_string=db_url,
    )
    logger.info("Ingestão concluída com sucesso.")


def sanitize_rag_chunk(text: str) -> str:
    """Higieniza fragmentos recuperados da base para impedir injeções indiretas de prompt."""
    if not text:
        return ""
    import re

    # Remove comandos de sistema e tags maliciosas que possam ter sido injetadas em arquivos .md
    clean = re.sub(r"(?i)\[system\]|\<system\>|\#\#\#\s*system|\[inst\]", "", text)
    clean = re.sub(
        r"(?i)\bignore\s+(all\s+)?(previous|prior|above)\s+instructions\b", "", clean
    )
    clean = re.sub(r"(?i)\besque[cç]a\s+(todas\s+as\s+)?regras\b", "", clean)
    return clean.strip()


KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "../../docs/knowledge_base")


def load_all_local_knowledge() -> str:
    """Lê todos os arquivos .md da base de conhecimento local como fallback garantido."""
    try:
        combined = []
        if os.path.exists(KNOWLEDGE_DIR):
            for filename in sorted(os.listdir(KNOWLEDGE_DIR)):
                if filename.endswith(".md"):
                    filepath = os.path.join(KNOWLEDGE_DIR, filename)
                    with open(filepath, encoding="utf-8") as f:
                        txt = f.read()
                        if txt.strip():
                            combined.append(f"--- {filename} ---\n{txt.strip()}")
        return "\n\n".join(combined)
    except Exception as e:
        logger.error(f"Erro ao carregar base local de markdown: {e}")
        return ""


def retrieve_context(query: str) -> str:
    """Busca o contexto mais relevante aplicando busca vetorial e garantindo leitura da base de conhecimento."""
    try:
        store = get_vectorstore()
        retriever = store.as_retriever(search_kwargs={"k": 3})
        docs = retriever.invoke(query)

        clean_chunks = [
            sanitize_rag_chunk(doc.page_content) for doc in docs if doc.page_content
        ]
        if clean_chunks:
            return "\n\n".join(clean_chunks)
    except Exception as e:
        logger.warning(
            f"Aviso na busca vetorial do PGVector ({e}). Acionando leitura direta dos arquivos RAG..."
        )

    # Fallback Garantido 100% à Prova de Falhas: lê os arquivos markdown atualizados da pasta knowledge_base
    return load_all_local_knowledge()

import os
import logging
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores.pgvector import PGVector

logger = logging.getLogger(__name__)

# Configurações do Banco. O langchain community usa psycopg2.
# Substituímos asyncpg caso exista na string.
db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ia_amanda")
if "+asyncpg" in db_url:
    db_url = db_url.replace("+asyncpg", "")

collection_name = "clinica_docs"

def get_embeddings():
    api_key = os.getenv("OPENAI_API_KEY")
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
    clean = re.sub(r"(?i)\bignore\s+(all\s+)?(previous|prior|above)\s+instructions\b", "", clean)
    clean = re.sub(r"(?i)\besque[cç]a\s+(todas\s+as\s+)?regras\b", "", clean)
    return clean.strip()

def retrieve_context(query: str) -> str:
    """Busca o contexto mais relevante para a pergunta aplicando filtro defensivo Zero-Trust."""
    store = get_vectorstore()
    retriever = store.as_retriever(search_kwargs={"k": 3})
    docs = retriever.invoke(query)
    
    clean_chunks = [sanitize_rag_chunk(doc.page_content) for doc in docs if doc.page_content]
    context = "\n\n".join(clean_chunks)
    return context

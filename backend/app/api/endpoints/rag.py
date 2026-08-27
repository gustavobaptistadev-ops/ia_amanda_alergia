from fastapi import APIRouter, HTTPException
import logging
import os
from pydantic import BaseModel
from langchain_core.documents import Document
from app.core.rag import get_vectorstore, get_embeddings, collection_name, db_url
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.pgvector import PGVector
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import async_session_maker

logger = logging.getLogger(__name__)
router = APIRouter()

KNOWLEDGE_FILE = os.path.join(os.path.dirname(__file__), '../../../docs/clinica_alergia_contexto.md')

class RagData(BaseModel):
    content: str

@router.get("/")
async def get_rag_context():
    """Retorna o texto atual da base de conhecimento (arquivo .md)."""
    try:
        if os.path.exists(KNOWLEDGE_FILE):
            with open(KNOWLEDGE_FILE, 'r', encoding='utf-8') as f:
                return {"content": f.read()}
        return {"content": ""}
    except Exception as e:
        logger.error(f"Erro ao ler base de conhecimento: {e}")
        raise HTTPException(status_code=500, detail="Erro ao ler o documento")

@router.post("/")
async def update_rag_context(data: RagData):
    """Atualiza o arquivo .md e re-ingere no PGVector."""
    try:
        # 1. Salvar no arquivo
        os.makedirs(os.path.dirname(KNOWLEDGE_FILE), exist_ok=True)
        with open(KNOWLEDGE_FILE, 'w', encoding='utf-8') as f:
            f.write(data.content)
            
        # 2. Apagar todos os vetores antigos do banco
        async with async_session_maker() as session:
            # O pgvector cria tabelas langchain_pg_embedding e langchain_pg_collection
            # Podemos apagar os embeddings associados à nossa collection
            query = text("""
                DELETE FROM langchain_pg_embedding 
                WHERE collection_id = (SELECT uuid FROM langchain_pg_collection WHERE name = :c_name)
            """)
            await session.execute(query, {"c_name": collection_name})
            await session.commit()
            
        # 3. Gerar novos vetores
        doc = Document(page_content=data.content)
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        docs = text_splitter.split_documents([doc])
        
        # 4. Inserir os novos vetores (como a collection já existe, o pgvector_from_documents só adiciona)
        # Importante: from_documents é síncrono no langchain_community PGVector
        PGVector.from_documents(
            embedding=get_embeddings(),
            documents=docs,
            collection_name=collection_name,
            connection_string=db_url,
        )
        
        return {"status": "ok", "message": "Base de conhecimento atualizada com sucesso!"}
    except Exception as e:
        logger.error(f"Erro ao atualizar RAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))

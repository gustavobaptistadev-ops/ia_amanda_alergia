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
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)
router = APIRouter()

KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), '../../../docs/knowledge_base')
os.makedirs(KNOWLEDGE_DIR, exist_ok=True)

from pydantic import BaseModel, Field

class RagData(BaseModel):
    filename: str = Field(..., max_length=100)
    content: str = Field(..., max_length=500_000) # Máximo 500 KB por documento RAG

@router.get("/")
async def list_rag_files():
    """Retorna a lista de arquivos da base de conhecimento."""
    try:
        files_data = []
        for filename in os.listdir(KNOWLEDGE_DIR):
            if filename.endswith(".md"):
                filepath = os.path.join(KNOWLEDGE_DIR, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    files_data.append({
                        "filename": filename,
                        "content": f.read()
                    })
        return files_data
    except Exception as e:
        logger.error(f"Erro ao ler base de conhecimento: {e}")
        raise HTTPException(status_code=500, detail="Erro ao ler os documentos")

import re

SAFE_FILENAME_REGEX = re.compile(r'^[a-zA-Z0-9_\-\.]+$')

def validate_safe_filename(filename: str) -> str:
    """Garante que o arquivo seja um .md seguro e impede Path Traversal."""
    clean_name = os.path.basename(filename).strip()
    if not clean_name.endswith('.md'):
        clean_name += '.md'
    if not SAFE_FILENAME_REGEX.match(clean_name) or '..' in clean_name:
        raise HTTPException(status_code=400, detail="Nome de arquivo inválido ou inseguro.")
    return clean_name

@router.post("/")
async def save_rag_file(data: RagData):
    """Salva um arquivo .md específico com proteção estrita contra Path Traversal."""
    try:
        clean_filename = validate_safe_filename(data.filename)
        filepath = os.path.join(KNOWLEDGE_DIR, clean_filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(data.content)
            
        return {"status": "ok", "message": "Arquivo salvo com sucesso!"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao salvar arquivo RAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{filename}")
async def delete_rag_file(filename: str):
    """Deleta um arquivo .md específico com proteção contra Path Traversal."""
    try:
        clean_filename = validate_safe_filename(filename)
        filepath = os.path.join(KNOWLEDGE_DIR, clean_filename)
        
        if os.path.exists(filepath):
            os.remove(filepath)
        return {"status": "ok", "message": "Arquivo deletado."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao deletar arquivo RAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/train")
async def train_rag():
    """Re-ingere todos os arquivos .md no PGVector."""
    try:
        # 1. Apagar todos os vetores antigos
        async with AsyncSessionLocal() as session:
            query = text("""
                DELETE FROM langchain_pg_embedding 
                WHERE collection_id = (SELECT uuid FROM langchain_pg_collection WHERE name = :c_name)
            """)
            await session.execute(query, {"c_name": collection_name})
            await session.commit()
            
        # 2. Ler e processar todos os arquivos
        docs = []
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        
        for filename in os.listdir(KNOWLEDGE_DIR):
            if filename.endswith(".md"):
                filepath = os.path.join(KNOWLEDGE_DIR, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if content.strip():
                        doc = Document(page_content=content, metadata={"source": filename})
                        docs.extend(text_splitter.split_documents([doc]))
        
        # 3. Inserir no banco
        if docs:
            PGVector.from_documents(
                embedding=get_embeddings(),
                documents=docs,
                collection_name=collection_name,
                connection_string=db_url,
            )
        
        return {"status": "ok", "message": "Treinamento concluído com sucesso!"}
    except Exception as e:
        logger.error(f"Erro ao treinar RAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))

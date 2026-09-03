from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List
import uuid

from app.database import AsyncSessionLocal
from app.models.learning import LearningSuggestion, LearningStatus
from app.core.security import get_api_key
import os
import datetime

router = APIRouter()

class LearningSuggestionResponse(BaseModel):
    id: str
    patient_name: str
    patient_phone: str
    suggestion_text: str
    context: str
    status: str
    created_at: str
    
    class Config:
        orm_mode = True

@router.get("/", response_model=List[LearningSuggestionResponse])
async def list_suggestions():
    async with AsyncSessionLocal() as session:
        stmt = select(LearningSuggestion).where(LearningSuggestion.status == LearningStatus.PENDING).order_by(LearningSuggestion.created_at.desc())
        result = await session.execute(stmt)
        suggestions = result.scalars().all()
        
        return [
            LearningSuggestionResponse(
                id=str(s.id),
                patient_name=s.patient_name or "Desconhecido",
                patient_phone=s.patient_phone or "",
                suggestion_text=s.suggestion_text,
                context=s.context,
                status=s.status,
                created_at=s.created_at.isoformat()
            ) for s in suggestions
        ]

@router.post("/{suggestion_id}/approve")
async def approve_suggestion(suggestion_id: str):
    async with AsyncSessionLocal() as session:
        sug = await session.get(LearningSuggestion, suggestion_id)
        if not sug:
            raise HTTPException(status_code=404, detail="Sugestão não encontrada")
            
        sug.status = LearningStatus.APPROVED
        sug.resolved_at = datetime.datetime.utcnow()
        await session.commit()
        
        # 1. Append to knowledge base
        KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), '../../../docs/knowledge_base')
        os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
        filepath = os.path.join(KNOWLEDGE_DIR, 'aprendizados_da_ia.md')
        
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(f"\n- [Regra Aprendida ({sug.resolved_at.strftime('%d/%m/%Y')})]: {sug.suggestion_text}\n")
            
        # 2. Trigger RAG re-train asynchronously
        from app.core.rag import get_vectorstore, get_embeddings, collection_name, db_url
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from langchain_community.vectorstores.pgvector import PGVector
        from langchain_core.documents import Document
        from sqlalchemy import text
        
        try:
            # We must run training in background ideally, but here we run it straight away for simplicity
            async with AsyncSessionLocal() as train_session:
                query = text("DELETE FROM langchain_pg_embedding WHERE collection_id = (SELECT uuid FROM langchain_pg_collection WHERE name = :c_name)")
                await train_session.execute(query, {"c_name": collection_name})
                await train_session.commit()
                
            docs = []
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
            
            for filename in os.listdir(KNOWLEDGE_DIR):
                if filename.endswith(".md"):
                    file_p = os.path.join(KNOWLEDGE_DIR, filename)
                    with open(file_p, 'r', encoding='utf-8') as file_obj:
                        content = file_obj.read()
                        if content.strip():
                            doc = Document(page_content=content, metadata={"source": filename})
                            docs.extend(text_splitter.split_documents([doc]))
            
            if docs:
                PGVector.from_documents(
                    embedding=get_embeddings(),
                    documents=docs,
                    collection_name=collection_name,
                    connection_string=db_url,
                )
        except Exception as e:
            # Revert status if train failed
            sug.status = LearningStatus.PENDING
            await session.commit()
            raise HTTPException(status_code=500, detail=f"Erro ao treinar RAG com o novo aprendizado: {e}")
            
        return {"status": "ok", "message": "Sugestão aprovada e Base de Conhecimento RAG atualizada com sucesso!"}

@router.post("/{suggestion_id}/reject")
async def reject_suggestion(suggestion_id: str):
    async with AsyncSessionLocal() as session:
        sug = await session.get(LearningSuggestion, suggestion_id)
        if not sug:
            raise HTTPException(status_code=404, detail="Sugestão não encontrada")
            
        sug.status = LearningStatus.REJECTED
        sug.resolved_at = datetime.datetime.utcnow()
        await session.commit()
        
        return {"status": "ok", "message": "Sugestão rejeitada."}

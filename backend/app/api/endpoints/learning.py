from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List
import uuid
import json

from app.database import AsyncSessionLocal
from app.models.learning import LearningSuggestion, LearningStatus
from app.core.security import get_api_key
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
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

class ClinicalCaseRequest(BaseModel):
    raw_case_text: str

@router.post("/ingest-clinical-cases")
async def ingest_clinical_case(request: ClinicalCaseRequest):
    """
    Recebe um relato bruto de caso clínico ou prontuário antigo, 
    anonimiza os dados via LLM, extrai as regras de triagem 
    e salva como LearningSuggestion para aprovação médica.
    """
    if not request.raw_case_text or len(request.raw_case_text) < 10:
        raise HTTPException(status_code=400, detail="O texto do caso deve ter pelo menos 10 caracteres.")

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", "Você é um assistente médico especialista em triagem de alergia. Sua tarefa é ler um relato clínico ou histórico de mensagens e estruturá-lo em um aprendizado para uma IA recepcionista.\n\n"
                   "REGRAS ESTRITAS:\n"
                   "1. REMOVA qualquer informação pessoal do paciente (nome, cpf, telefone). Use termos genéricos (ex: Paciente, Mãe, etc).\n"
                   "2. Estruture sua resposta EXATAMENTE no seguinte formato:\n\n"
                   "Sintoma Relatado: [Resumo do sintoma]\n"
                   "Acolhimento Sugerido: [Como a IA deve acolher a dor empatia]\n"
                   "Perguntas Chave a Fazer: [Quais perguntas a IA deve fazer para a triagem]\n"
                   "Ação de Triagem: [O que a IA deve sugerir no final, ex: Agendar encaixe urgente, orientar PS, agendar consulta eletiva]\n\n"
                   "Lembre-se: A IA recepcionista é PROIBIDA de prescrever medicamentos ou diagnosticar. Foque apenas na coleta de dados e encaminhamento."),
        ("user", "Texto Bruto do Caso:\n{raw_text}")
    ])
    
    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
        chain = prompt_template | llm
        
        response = await chain.ainvoke({"raw_text": request.raw_case_text})
        extracted_learning = response.content.strip()
        
        async with AsyncSessionLocal() as session:
            new_sug = LearningSuggestion(
                id=uuid.uuid4(),
                patient_name="Caso Clínico Importado",
                patient_phone="",
                suggestion_text=extracted_learning,
                context="Ingestão em Lote via API (Anonimizado)",
                status=LearningStatus.PENDING,
                created_at=datetime.datetime.utcnow()
            )
            session.add(new_sug)
            await session.commit()
            
        return {"status": "ok", "message": "Caso clínico processado, anonimizado e aguardando aprovação no painel."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar o caso via LLM: {str(e)}")

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
        # Modificação: Se for caso clínico importado, salvar na pasta correta
        KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), '../../../docs/knowledge_base')
        os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
        
        if sug.context == "Ingestão em Lote via API (Anonimizado)":
            filepath = os.path.join(KNOWLEDGE_DIR, '06_casos_clinicos_referencia.md')
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write(f"\n### Caso Adicionado em {sug.resolved_at.strftime('%d/%m/%Y')}\n{sug.suggestion_text}\n---\n")
        else:
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

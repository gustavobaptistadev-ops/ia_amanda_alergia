import asyncio
import argparse
import json
import csv
import os
import sys

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Ensure backend root is in PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- MOCKING DA DATABASE E CHECKPOINTER PARA TESTE EM LOTE ---
class MockSession:
    async def __aenter__(self): return self
    async def __aexit__(self, exc_type, exc_val, exc_tb): pass
    async def execute(self, stmt):
        class MockResult:
            def scalars(self):
                class MockScalars:
                    def first(self): return None
                return MockScalars()
        return MockResult()
    def add(self, *args, **kwargs): pass
    async def commit(self): pass
    async def refresh(self, *args, **kwargs): pass

def mock_async_session_local():
    return MockSession()

import app.database
app.database.AsyncSessionLocal = mock_async_session_local

import app.services.db_service
app.services.db_service.AsyncSessionLocal = mock_async_session_local

import app.core.orchestrator
app.core.orchestrator.AsyncSessionLocal = mock_async_session_local

from langgraph.checkpoint.memory import MemorySaver
async def mock_init_checkpointer():
    app.core.orchestrator._checkpointer = MemorySaver()
    app.core.orchestrator.app_graph = app.core.orchestrator.workflow.compile(checkpointer=app.core.orchestrator._checkpointer)

app.core.orchestrator.init_checkpointer = mock_init_checkpointer
# --- FIM DO MOCKING ---

from app.services.langflow_client import evaluate_transcript_via_langflow
from app.services.db_service import save_learning_suggestion
from app.core.input_shield import detect_emergency, EMERGENCY_RESPONSE, detect_adversarial_attempt
from app.core.orchestrator import process_user_message
from app.core.guardrails import validar_resposta

async def process_cases(filepath: str, max_cases: int = None):
    print(f"Lendo casos clínicos de: {filepath}")
    
    cases = []
    if filepath.endswith(".csv"):
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')
            cases = list(reader)
    else:
        print("Formato não suportado. Use .csv")
        return

    if max_cases:
        cases = cases[:max_cases]

    print(f"Iniciando avaliação em lote para {len(cases)} casos no Langflow...")

    report = "# Relatório de Avaliação em Lote (Langflow)\n\n"

    for idx, case in enumerate(cases):
        patient_name = case.get("patient_name", f"Paciente {idx}")
        message = case.get("message", "")
        intent = case.get("intent", "")
        expected_action = case.get("expected_bot_action", "")
        thread_id = f"batch_eval_{idx}"

        if not message:
            print(f"[!] Caso {idx} ignorado: Sem mensagem.")
            continue

        print(f"\n[{idx+1}/{len(cases)}] Paciente: {patient_name}")
        print(f"  -> Input: {message}")
        print(f"  -> Intenção Esperada: {intent}")
        print(f"  -> Ação Esperada: {expected_action}")
        
        report += f"## {idx+1}. {patient_name}\n"
        report += f"- **Input do Paciente:** `{message}`\n"
        report += f"- **Intenção Esperada:** `{intent}`\n"
        report += f"- **Ação Esperada:** `{expected_action}`\n\n"

        # Simula o fluxo do bot
        try:
            if detect_emergency(message):
                response = f"[BLOCKED BY SHIELD - EMERGENCY] {EMERGENCY_RESPONSE}"
            elif await detect_adversarial_attempt(message):
                response = "[BLOCKED BY SHIELD - ADVERSARIAL] Por segurança, não posso responder."
            else:
                raw_response = await process_user_message(thread_id=thread_id, message=message)
                if not validar_resposta(raw_response):
                    response = "[BLOCKED BY OUTPUT GUARDRAIL] Prescrições proibidas."
                else:
                    response = raw_response

            print(f"  -> Output (Amanda): {response}")
            report += f"**Output da IA (Amanda):**\n> {response}\n\n"
            
            transcript = f"Paciente: {message}\nAmanda: {response}"
            
            # Avaliação via Langflow
            suggestion = await evaluate_transcript_via_langflow(transcript, thread_id)
            
            if suggestion and suggestion.upper() != "NONE":
                print(f"  -> Sugestão do Langflow: {suggestion}")
                report += f"**Sugestão de Correção (Langflow):** {suggestion}\n\n"
                await save_learning_suggestion(
                    contact_id=thread_id,
                    patient_name=patient_name,
                    patient_phone="0000000000",
                    suggestion_text=suggestion,
                    context="Auditoria Clínica Lote (Langflow)"
                )
            else:
                print("  -> Nenhuma sugestão (Atendimento Perfeito).")
                report += f"**Sugestão de Correção (Langflow):** Nenhuma (Atendimento Perfeito).\n\n"
                
            report += "---\n\n"
                
        except Exception as e:
            print(f"  [ERRO] Falha ao processar caso {idx}: {e}")
            report += f"**ERRO NO SISTEMA:** {e}\n\n---\n\n"

    # Salva o relatório
    report_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "evaluation_report_batch.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
        
    print(f"\nAvaliação em Lote finalizada! Relatório gerado em: {report_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script de Ingestão de Casos Clínicos no Langflow")
    parser.add_argument("--file", type=str, required=True, help="Caminho para o arquivo .csv")
    parser.add_argument("--limit", type=int, help="Número máximo de casos para testar", default=None)
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(f"Arquivo não encontrado: {args.file}")
        sys.exit(1)
        
    asyncio.run(process_cases(args.file, args.limit))

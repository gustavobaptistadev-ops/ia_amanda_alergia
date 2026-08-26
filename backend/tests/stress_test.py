import asyncio
import httpx
import time

WEBHOOK_URL = "http://localhost:8000/api/v1/webhook/evolution"

# Simula N pacientes diferentes mandando mensagem ao mesmo tempo.
# Isso testa a concorrência do LangGraph e a isolação da memória no Redis (Threads separadas).

async def simulate_patient(client: httpx.AsyncClient, patient_id: int):
    phone = f"551199999{patient_id:04d}@s.whatsapp.net"
    
    # Payload simulado do Evolution GO (messages.upsert)
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {
                "remoteJid": phone,
                "fromMe": False
            },
            "message": {
                "conversation": f"Olá! Sou o paciente {patient_id}. Quero saber o valor da consulta."
            }
        }
    }
    
    start_time = time.time()
    try:
        response = await client.post(WEBHOOK_URL, json=payload, timeout=30.0)
        elapsed = time.time() - start_time
        print(f"✅ Paciente {patient_id} respondido em {elapsed:.2f}s | Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Paciente {patient_id} falhou: {e}")

async def main():
    NUM_PATIENTS = 10  # Quantidade de pacientes simultâneos
    print(f"🚀 Iniciando teste de estresse com {NUM_PATIENTS} pacientes simultâneos...")
    
    start_total = time.time()
    
    async with httpx.AsyncClient() as client:
        tasks = [simulate_patient(client, i) for i in range(1, NUM_PATIENTS + 1)]
        await asyncio.gather(*tasks)
        
    elapsed_total = time.time() - start_total
    print(f"🏁 Teste concluído em {elapsed_total:.2f}s!")

if __name__ == "__main__":
    asyncio.run(main())

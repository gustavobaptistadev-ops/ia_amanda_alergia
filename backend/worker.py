import asyncio
import os
import logging
from arq import Worker
from arq.connections import RedisSettings
from dotenv import load_dotenv

# Carregar variáveis de ambiente (necessário para DB e OpenAI dentro do worker)
load_dotenv()

# Configuração de Log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker")

# Função que será processada em background
async def process_message_job(ctx, data: dict):
    logger.info(f"Worker recebeu job de webhook. Iniciando processamento...")
    # Importar aqui para evitar circular imports e garantir que carrega pós-fork
    from app.services.message_processor import process_message
    await process_message(data)
    logger.info("Worker finalizou o job.")

# Configurações do Redis para o arq
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
# Parse simples de url de redis para o arq RedisSettings
import urllib.parse
parsed = urllib.parse.urlparse(redis_url)
host = parsed.hostname or 'localhost'
port = parsed.port or 6379
password = parsed.password
database = int(parsed.path.replace('/', '')) if parsed.path and parsed.path != '/' else 0

redis_settings = RedisSettings(host=host, port=port, password=password, database=database)

class WorkerSettings:
    functions = [process_message_job]
    redis_settings = redis_settings
    # Quantidade de jobs simultâneos
    max_jobs = 10
    # Políticas de Retry e Timeout para falhas de LLM / Rede
    max_tries = 3
    job_timeout = 300
    # Opcional: configurar startup e shutdown callbacks se necessário

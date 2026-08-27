#!/bin/bash
# Aplica as migrações do banco de dados (ignorando se já estiverem feitas)
echo "Rodando migrações do banco (Alembic)..."
alembic upgrade head

# Inicia o worker assíncrono (arq) em background
echo "Iniciando Arq Worker (Redis)..."
arq worker.WorkerSettings &

# Inicia o servidor principal do FastAPI
echo "Iniciando FastAPI..."
uvicorn app.main:app --host 0.0.0.0 --port $PORT

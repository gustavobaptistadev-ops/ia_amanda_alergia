#!/bin/bash
set -euo pipefail

# Fail before migrations if the deployment is missing security configuration.
required_secrets=(INTERNAL_API_KEY WEBHOOK_SECRET JWT_SECRET_KEY ENCRYPTION_KEY)
for secret_name in "${required_secrets[@]}"; do
  secret_value="$(printenv "${secret_name}" || true)"
  if [ "${#secret_value}" -lt 32 ]; then
    echo "Missing or weak required secret: ${secret_name}" >&2
    exit 1
  fi
done

# Aplica as migrações do banco de dados (ignorando se já estiverem feitas)
echo "Rodando migrações do banco (Alembic)..."
alembic upgrade head

# Inicia o worker assíncrono (arq) em background
echo "Iniciando Arq Worker (Redis)..."
arq worker.WorkerSettings &

# Inicia o servidor principal do FastAPI
echo "Iniciando FastAPI..."
uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"

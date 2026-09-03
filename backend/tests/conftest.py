import os
import sys
from pathlib import Path


# Ensure tests import the application package from this backend checkout.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
backend_root = str(BACKEND_ROOT)
if backend_root in sys.path:
    sys.path.remove(backend_root)
sys.path.insert(0, backend_root)

# Security modules fail closed in production. Tests use explicit non-production values.
os.environ.setdefault("INTERNAL_API_KEY", "test-internal-api-key-at-least-32-characters")
os.environ.setdefault("WEBHOOK_SECRET", "test-webhook-secret-at-least-32-characters")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-at-least-32-characters")

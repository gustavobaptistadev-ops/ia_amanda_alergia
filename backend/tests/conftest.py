import sys
from pathlib import Path


# Ensure tests import the application package from this backend checkout.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
backend_root = str(BACKEND_ROOT)
if backend_root in sys.path:
    sys.path.remove(backend_root)
sys.path.insert(0, backend_root)

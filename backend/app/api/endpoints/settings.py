import os
import json
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "../../../settings_ai.json")

class AIConfig(BaseModel):
    model: str = "gpt-4o-mini"
    temperature: float = 0.35
    max_tokens: int = 1000
    persona_name: str = "Amanda"
    voice_reply_enabled: bool = False
    voice_name: str = "nova"
    semantic_cache_enabled: bool = True

def load_config() -> dict:
    default_cfg = {
        "model": "gpt-4o-mini",
        "temperature": 0.35,
        "max_tokens": 1000,
        "persona_name": "Amanda",
        "voice_reply_enabled": False,
        "voice_name": "nova",
        "semantic_cache_enabled": True
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return {**default_cfg, **json.load(f)}
        except Exception as e:
            logger.error(f"Erro ao ler settings_ai.json: {e}")
    return default_cfg

@router.get("/")
async def get_ai_settings():
    """Retorna as configurações atuais do modelo de IA."""
    return load_config()

@router.post("/")
async def update_ai_settings(config: AIConfig):
    """Atualiza as configurações do modelo de IA."""
    try:
        data = config.dict()
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return {"status": "ok", "message": "Configurações de IA salvas com sucesso!", "config": data}
    except Exception as e:
        logger.error(f"Erro ao salvar configurações de IA: {e}")
        raise HTTPException(status_code=500, detail="Falha ao salvar configurações.")

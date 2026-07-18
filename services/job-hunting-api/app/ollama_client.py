import httpx

from app.config import settings


async def check_ollama() -> dict:
    url = f"{settings.ollama_base_url.rstrip('/')}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            models = [item.get("name", "") for item in response.json().get("models", [])]
            return {"ok": True, "models": models}
    except Exception as exc:  # noqa: BLE001 - smoke endpoint should never 500 on Ollama down
        return {"ok": False, "error": str(exc), "models": []}


async def generate(prompt: str) -> str:
    url = f"{settings.ollama_base_url.rstrip('/')}/api/generate"
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json().get("response", "")

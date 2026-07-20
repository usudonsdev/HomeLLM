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
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc), "models": []}


def _format_http_error(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        body = (exc.response.text or "")[:500]
        return f"{exc.response.status_code} {exc.response.reason_phrase}: {body}"
    if isinstance(exc, httpx.TimeoutException):
        return f"timeout after {settings.ollama_timeout_seconds}s ({type(exc).__name__})"
    msg = str(exc).strip()
    return msg or type(exc).__name__


async def generate(prompt: str) -> str:
    url = f"{settings.ollama_base_url.rstrip('/')}/api/generate"
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": settings.ollama_keep_alive,
    }
    timeout = httpx.Timeout(settings.ollama_timeout_seconds)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(_format_http_error(exc)) from exc

    answer = data.get("response")
    if answer is None:
        raise RuntimeError(f"Ollama response missing 'response' field: {str(data)[:500]}")
    return answer

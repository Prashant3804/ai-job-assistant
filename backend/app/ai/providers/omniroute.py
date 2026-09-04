import json
import logging
import re
from typing import List, Dict, Any, Optional, Type, TypeVar
import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.ai.interfaces.llm_provider import LLMProvider
from app.ai.interfaces.embedding_provider import EmbeddingProvider

logger = logging.getLogger("omniroute_provider")
T = TypeVar("T", bound=BaseModel)

class OmniRouteLLMProvider(LLMProvider):
    """OmniRoute OpenAI-compatible LLM provider."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None
    ):
        self.base_url = (base_url or settings.OMNIROUTE_BASE_URL).rstrip("/")
        self.api_key = api_key or settings.OMNIROUTE_API_KEY
        self.model = model or settings.OMNIROUTE_CHAT_MODEL
        self.timeout = timeout or float(settings.OMNIROUTE_TIMEOUT_SECONDS)
        self.max_retries = max_retries or settings.OMNIROUTE_MAX_RETRIES

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        req_timeout = timeout or self.timeout
        last_exception = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"OmniRoute chat completion attempt {attempt}/{self.max_retries} with model {self.model}")
                async with httpx.AsyncClient(timeout=req_timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=self._get_headers(),
                        json=payload
                    )
                    response.raise_for_status()
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    return content
            except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as e:
                last_exception = e
                logger.warning(f"OmniRoute request failed (attempt {attempt}/{self.max_retries}): {type(e).__name__}")
                if attempt == self.max_retries:
                    break

        raise RuntimeError(f"OmniRoute LLM generation failed after {self.max_retries} attempts: {last_exception}")

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: Optional[str],
        response_model: Type[T],
        temperature: float = 0.1,
        timeout: Optional[float] = None
    ) -> T:
        schema = response_model.model_json_schema()
        system_instruction = (
            (system_prompt or "") +
            f"\nYou must respond strictly with a valid JSON object matching this schema:\n{json.dumps(schema)}"
        )

        raw_text = await self.generate_text(
            prompt=prompt,
            system_prompt=system_instruction,
            temperature=temperature,
            timeout=timeout
        )

        clean_json = re.sub(r"^```(?:json)?\s*", "", raw_text.strip())
        clean_json = re.sub(r"\s*```$", "", clean_json.strip())

        try:
            parsed = json.loads(clean_json)
            return response_model.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Failed to parse or validate OmniRoute structured output: {e}")
            raise ValueError(f"Invalid structured response from OmniRoute: {e}")

    async def check_health(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/models", headers=self._get_headers())
                if res.status_code == 200:
                    return {
                        "configured": bool(self.api_key),
                        "reachable": True,
                        "auth_valid": True,
                        "status": "CONNECTED",
                        "model": self.model,
                        "base_url": self.base_url,
                        "message": "OmniRoute gateway reachable and responsive"
                    }
                elif res.status_code in (401, 403):
                    return {
                        "configured": bool(self.api_key),
                        "reachable": True,
                        "auth_valid": False,
                        "status": "DEGRADED",
                        "model": self.model,
                        "base_url": self.base_url,
                        "message": "OmniRoute gateway reachable but authentication failed"
                    }
                else:
                    return {
                        "configured": bool(self.api_key),
                        "reachable": True,
                        "auth_valid": False,
                        "status": "DEGRADED",
                        "model": self.model,
                        "base_url": self.base_url,
                        "message": f"OmniRoute returned HTTP {res.status_code}"
                    }
        except Exception as e:
            return {
                "configured": bool(self.api_key),
                "reachable": False,
                "auth_valid": False,
                "status": "OFFLINE",
                "model": self.model,
                "base_url": self.base_url,
                "message": f"OmniRoute unreachable: {type(e).__name__}"
            }


class OmniRouteEmbeddingProvider(EmbeddingProvider):
    """OmniRoute OpenAI-compatible Embedding provider."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None
    ):
        self.base_url = (base_url or settings.OMNIROUTE_BASE_URL).rstrip("/")
        self.api_key = api_key or settings.OMNIROUTE_API_KEY
        self.model = model or settings.OMNIROUTE_EMBEDDING_MODEL
        self.timeout = timeout or float(settings.OMNIROUTE_TIMEOUT_SECONDS)

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def get_model_name(self) -> str:
        return self.model

    async def generate_embedding(self, text: str, timeout: Optional[float] = None) -> List[float]:
        req_timeout = timeout or self.timeout
        payload = {
            "model": self.model,
            "input": text
        }
        try:
            logger.info(f"Generating embedding with OmniRoute model {self.model}")
            async with httpx.AsyncClient(timeout=req_timeout) as client:
                res = await client.post(
                    f"{self.base_url}/embeddings",
                    headers=self._get_headers(),
                    json=payload
                )
                res.raise_for_status()
                data = res.json()
                return data["data"][0]["embedding"]
        except Exception as e:
            logger.error(f"OmniRoute embedding generation failed: {type(e).__name__}")
            raise RuntimeError(f"OmniRoute embedding failure: {e}")

    async def check_health(self) -> Dict[str, Any]:
        try:
            # Test small embedding call
            vec = await self.generate_embedding("health check", timeout=4.0)
            return {
                "configured": bool(self.api_key),
                "reachable": True,
                "embedding_available": True,
                "dimension": len(vec),
                "model": self.model,
                "message": "Embedding endpoint active"
            }
        except Exception as e:
            return {
                "configured": bool(self.api_key),
                "reachable": False,
                "embedding_available": False,
                "model": self.model,
                "message": f"Embedding check failed: {type(e).__name__}"
            }

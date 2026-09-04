from abc import ABC, abstractmethod
from typing import Optional, Type, TypeVar, Dict, Any, List
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

class LLMProvider(ABC):
    """Abstract interface for LLM text generation and structured outputs."""

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None
    ) -> str:
        """Generate unstructured text from prompt."""
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        system_prompt: Optional[str],
        response_model: Type[T],
        temperature: float = 0.1,
        timeout: Optional[float] = None
    ) -> T:
        """Generate and validate a structured response using Pydantic."""
        pass

    @abstractmethod
    async def check_health(self) -> Dict[str, Any]:
        """Check provider connectivity and configuration status safely."""
        pass

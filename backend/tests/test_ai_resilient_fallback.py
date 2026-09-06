import pytest
from unittest.mock import AsyncMock, patch
from app.modules.ai.service import ResilientAIService, GeminiProvider, OpenRouterProvider
from pydantic import BaseModel

class SampleSchema(BaseModel):
    summary: str
    skills: list[str]

@pytest.mark.asyncio
async def test_gemini_success_primary():
    service = ResilientAIService()
    service.gemini = AsyncMock(spec=GeminiProvider)
    service.gemini.generate_text.return_value = 'Gemini output'
    
    res = await service.generate_text('test prompt')
    assert res == 'Gemini output'
    assert service.last_provider_used == 'gemini'
    assert not service.last_fallback_occurred

@pytest.mark.asyncio
async def test_gemini_failure_fallback_to_openrouter():
    service = ResilientAIService()
    service.gemini = AsyncMock(spec=GeminiProvider)
    service.gemini.generate_text.side_effect = Exception('Gemini 429 Quota Exceeded')
    
    service.openrouter = AsyncMock(spec=OpenRouterProvider)
    service.openrouter.generate_text.return_value = 'OpenRouter fallback output'
    
    res = await service.generate_text('test prompt')
    assert res == 'OpenRouter fallback output'
    assert service.last_provider_used == 'openrouter'
    assert service.last_fallback_occurred

@pytest.mark.asyncio
async def test_both_fail_deterministic_local_fallback():
    service = ResilientAIService()
    service.gemini = AsyncMock(spec=GeminiProvider)
    service.gemini.generate_text.side_effect = Exception('Gemini Down')
    service.openrouter = AsyncMock(spec=OpenRouterProvider)
    service.openrouter.generate_text.side_effect = Exception('OpenRouter Down')
    
    res = await service.generate_text('test prompt')
    assert isinstance(res, str)
    assert len(res) > 0
    assert service.last_provider_used == 'mock'

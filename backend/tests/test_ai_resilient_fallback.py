import pytest
from unittest.mock import AsyncMock, patch
from app.modules.ai.service import ResilientAIService, GeminiProvider, OmniRouteProvider, AIServiceException
from pydantic import BaseModel

class SampleSchema(BaseModel):
    summary: str
    skills: list[str]

@pytest.mark.asyncio
async def test_1_gemini_success_primary():
    """Test 1: Gemini succeeds -> Provider = Gemini, zero fallback."""
    service = ResilientAIService()
    service.gemini = AsyncMock(spec=GeminiProvider)
    service.gemini.generate_text.return_value = 'Gemini output'
    
    res = await service.generate_text('test prompt')
    assert res == 'Gemini output'
    assert service.last_provider_used == 'gemini'
    assert not service.last_fallback_occurred
    assert service.last_fallback_reason is None

@pytest.mark.asyncio
async def test_2_gemini_429_fallback_to_omniroute():
    """Test 2: Gemini returns 429 -> Automatic fallback to OmniRoute."""
    service = ResilientAIService()
    service.gemini = AsyncMock(spec=GeminiProvider)
    service.gemini.generate_text.side_effect = Exception('HTTP 429 Quota Exceeded / Rate Limited')
    
    service.omniroute = AsyncMock(spec=OmniRouteProvider)
    service.omniroute.generate_text.return_value = 'OmniRoute fallback output'
    
    res = await service.generate_text('test prompt')
    assert res == 'OmniRoute fallback output'
    assert service.last_provider_used == 'omniroute'
    assert service.last_fallback_occurred is True
    assert '429' in service.last_fallback_reason

@pytest.mark.asyncio
async def test_3_gemini_timeout_fallback_to_omniroute():
    """Test 3: Gemini times out -> Automatic fallback to OmniRoute."""
    service = ResilientAIService()
    service.gemini = AsyncMock(spec=GeminiProvider)
    service.gemini.generate_text.side_effect = Exception('Request timed out after 30.0s')
    
    service.omniroute = AsyncMock(spec=OmniRouteProvider)
    service.omniroute.generate_text.return_value = 'OmniRoute timeout fallback output'
    
    res = await service.generate_text('test prompt')
    assert res == 'OmniRoute timeout fallback output'
    assert service.last_provider_used == 'omniroute'
    assert service.last_fallback_occurred is True
    assert 'timeout' in service.last_fallback_reason.lower()

@pytest.mark.asyncio
async def test_4_gemini_5xx_fallback_to_omniroute():
    """Test 4: Gemini returns retryable 5xx -> Automatic fallback to OmniRoute."""
    service = ResilientAIService()
    service.gemini = AsyncMock(spec=GeminiProvider)
    service.gemini.generate_text.side_effect = Exception('Gemini 503 Service Unavailable')
    
    service.omniroute = AsyncMock(spec=OmniRouteProvider)
    service.omniroute.generate_text.return_value = 'OmniRoute 5xx fallback output'
    
    res = await service.generate_text('test prompt')
    assert res == 'OmniRoute 5xx fallback output'
    assert service.last_provider_used == 'omniroute'
    assert service.last_fallback_occurred is True
    assert '5xx' in service.last_fallback_reason

@pytest.mark.asyncio
async def test_5_both_fail_controlled_ai_service_exception():
    """Test 5: Both providers fail -> Controlled AIServiceException with no fabricated AI output."""
    service = ResilientAIService()
    service.gemini = AsyncMock(spec=GeminiProvider)
    service.gemini.generate_text.side_effect = Exception('Gemini 429 Quota Exceeded')
    service.omniroute = AsyncMock(spec=OmniRouteProvider)
    service.omniroute.generate_text.side_effect = Exception('OmniRoute endpoint unreachable')
    
    with pytest.raises(AIServiceException) as exc_info:
        await service.generate_text('test prompt')
    
    assert 'All resilient AI providers failed' in str(exc_info.value)
    assert 'Gemini' in str(exc_info.value)
    assert 'OmniRoute' in str(exc_info.value)

@pytest.mark.asyncio
async def test_6_provider_status_matches_contract():
    """Test 6: Provider status matches canonical Gemini -> OmniRoute architecture."""
    service = ResilientAIService()
    service.gemini_key = 'test-gemini-key'
    service.omniroute_key = 'test-omniroute-key'
    
    # Initial status (Gemini primary active)
    status = service.get_provider_status()
    assert status['primary_provider'] == 'gemini'
    assert status['primary_status'] == 'AVAILABLE'
    assert status['fallback_provider'] == 'omniroute'
    assert status['fallback_status'] == 'AVAILABLE'
    assert status['routing'] == 'Gemini -> OmniRoute'
    assert status['active_provider'] == 'gemini'
    assert status['active_display'] == 'Gemini (Primary)'
    assert status['automatic_fallback_enabled'] is True

    # Fallback status when fallback occurs
    service.last_fallback_occurred = True
    service.last_fallback_reason = 'Gemini rate limit (429)'
    status_after = service.get_provider_status()
    assert status_after['active_provider'] == 'omniroute'
    assert status_after['active_display'] == 'OmniRoute (Fallback Active)'
    assert status_after['last_fallback_occurred'] is True
    assert status_after['last_fallback_reason'] == 'Gemini rate limit (429)'

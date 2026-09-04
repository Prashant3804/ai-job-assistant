import pytest
from app.core.security import verify_password, get_password_hash, create_access_token, decode_token
from app.modules.auth.service import AuthService
from app.shared.schemas import UserRegisterRequest, UserLoginRequest
from app.core.exceptions import DuplicateEntityError, InvalidCredentialsError

@pytest.mark.asyncio
async def test_password_hashing():
    raw_pass = "SecurePass123!"
    hashed = get_password_hash(raw_pass)
    assert hashed != raw_pass
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

@pytest.mark.asyncio
async def test_jwt_token_flow():
    user_id = "11111111-2222-3333-4444-555555555555"
    token = create_access_token(user_id)
    assert token is not None
    decoded = decode_token(token)
    assert decoded == user_id

@pytest.mark.asyncio
async def test_user_registration_and_login(async_session):
    service = AuthService(async_session)
    reg_payload = UserRegisterRequest(
        email="jane.doe@example.com",
        password="MySecretPassword123",
        full_name="Jane Doe"
    )
    user = await service.register_user(reg_payload)
    assert user.email == "jane.doe@example.com"
    assert user.full_name == "Jane Doe"
    assert user.profile is not None
    assert user.job_preferences is not None

    # Test duplicate registration rejection
    with pytest.raises(DuplicateEntityError):
        await service.register_user(reg_payload)

    # Test successful login
    login_payload = UserLoginRequest(email="jane.doe@example.com", password="MySecretPassword123")
    token_resp = await service.authenticate_user(login_payload)
    assert token_resp.access_token is not None
    assert token_resp.user.email == "jane.doe@example.com"

    # Test invalid password rejection
    bad_login = UserLoginRequest(email="jane.doe@example.com", password="IncorrectPassword")
    with pytest.raises(InvalidCredentialsError):
        await service.authenticate_user(bad_login)

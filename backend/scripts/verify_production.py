import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings

def run_environment_verification():
    print("=" * 60)
    print("AI JOB ASSISTANT — SAFE PRODUCTION CONFIGURATION AUDIT")
    print("=" * 60)

    # 1. Database
    db_configured = bool(settings.DATABASE_URL)
    db_dialect = "PostgreSQL (asyncpg)" if "postgres" in settings.get_db_url() else "SQLite (aiosqlite)"
    print(f"DATABASE:               {'CONFIGURED [OK]' if db_configured else 'NOT_CONFIGURED [MISSING]'} ({db_dialect})")

    # 2. Server Port & Storage
    print(f"SERVER BINDING:         {settings.HOST}:{settings.PORT}")
    print(f"STORAGE DIRECTORY:      {settings.STORAGE_DIR}")

    # 3. OmniRoute
    omni_configured = bool(settings.OMNIROUTE_API_KEY and settings.OMNIROUTE_API_KEY != "mock-omniroute-key")
    print(f"OMNIROUTE AI GATEWAY:   {'CONFIGURED [OK]' if omni_configured else 'NOT_CONFIGURED (Fallback Mock Active)'}")

    # 4. Gmail OAuth
    gmail_configured = bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)
    gmail_prod_redirect = "localhost" not in settings.GOOGLE_REDIRECT_URI and "127.0.0.1" not in settings.GOOGLE_REDIRECT_URI
    print(f"GMAIL OAUTH:            {'CONFIGURED [OK]' if gmail_configured else 'NOT_CONFIGURED (Mock Authorized Mode)'}")
    print(f"GMAIL REDIRECT URI:     {settings.GOOGLE_REDIRECT_URI} ({'PROD DOMAIN' if gmail_prod_redirect else 'LOCAL DEV'})")

    # 5. Microsoft Outlook OAuth
    outlook_configured = bool(settings.MICROSOFT_CLIENT_ID and settings.MICROSOFT_CLIENT_SECRET)
    outlook_prod_redirect = "localhost" not in settings.MICROSOFT_REDIRECT_URI and "127.0.0.1" not in settings.MICROSOFT_REDIRECT_URI
    print(f"OUTLOOK OAUTH:          {'CONFIGURED [OK]' if outlook_configured else 'NOT_CONFIGURED (Mock Authorized Mode)'}")
    print(f"OUTLOOK REDIRECT URI:   {settings.MICROSOFT_REDIRECT_URI} ({'PROD DOMAIN' if outlook_prod_redirect else 'LOCAL DEV'})")

    # 6. CORS Configuration
    cors_list = settings.BACKEND_CORS_ORIGINS if isinstance(settings.BACKEND_CORS_ORIGINS, list) else [settings.BACKEND_CORS_ORIGINS]
    cors_safe = "*" not in cors_list
    print(f"CORS ORIGINS:           {len(cors_list)} origin(s) configured ({'STRICT / NO WILDCARD [OK]' if cors_safe else 'WARNING: WILDCARD DETECTED'})")

    # 7. Encryption Key & Auth Secret
    enc_configured = bool(settings.MAILBOX_ENCRYPTION_KEY and "supersecret" not in settings.MAILBOX_ENCRYPTION_KEY.lower())
    print(f"TOKEN ENCRYPTION:       {'CONFIGURED [OK]' if enc_configured else 'DEFAULT DEV KEY'}")

    auth_configured = bool(settings.SECRET_KEY and "supersecretkey" not in settings.SECRET_KEY.lower() and len(settings.SECRET_KEY) >= 32)
    print(f"AUTH JWT SECURITY:      {'CONFIGURED [OK]' if auth_configured else 'DEFAULT DEV SECRET'}")

    # 8. Worker Settings
    print(f"WORKER LEASE TIMEOUT:   {settings.WORKER_LEASE_SECONDS}s")
    print(f"WORKER HEARTBEAT:       {settings.WORKER_HEARTBEAT_SECONDS}s")
    print(f"ENVIRONMENT:            {settings.ENVIRONMENT}")
    print("=" * 60)

    issues = settings.validate_production_configuration()
    if issues:
        print("\nProduction Recommendations:")
        for iss in issues:
            print(f"  - {iss}")
    else:
        print("\nAll production security and configuration guards verified.")
    print("=" * 60)

if __name__ == "__main__":
    run_environment_verification()

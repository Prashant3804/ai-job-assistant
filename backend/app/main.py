import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.database.session import init_db
from app.core.middleware import RequestLoggingMiddleware
from app.modules.auth.router import router as auth_router
from app.modules.resume.router import router as resume_router
from app.modules.jobs.router import router as jobs_router
from app.modules.matching.router import router as matching_router
from app.modules.applications.router import router as applications_router
from app.modules.email.router import router as email_router
from app.modules.chat.router import router as chat_router
from app.modules.integrations.router import router as integrations_router
from app.modules.analytics.router import router as analytics_router
from app.modules.mailbox.router import router as mailbox_router
from app.modules.communication.router import router as communication_router, interviews_router
from app.modules.system.router import health_router, system_router, connectors_router
from app.modules.system.settings_router import router as settings_router
from app.modules.system.onboarding_router import router as onboarding_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} [{settings.ENVIRONMENT}]...")
    issues = settings.validate_production_configuration()
    if issues:
        for iss in issues:
            logger.error(f"[CONFIG CRITICAL] {iss}")
        if settings.ENVIRONMENT.lower() == "production":
            raise RuntimeError(f"Production configuration failed validation: {'; '.join(issues)}")

    logger.info("Initializing database schema...")
    await init_db()
    logger.info("Database schema initialized.")
    yield
    logger.info("Shutting down AI Job Assistant service.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Production-quality AI Job Search & Application Assistant API with pgvector, LLM orchestration, and compliance guards.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add Request Logging & Rate Limiting Middleware
app.add_middleware(RequestLoggingMiddleware)

# Configure CORS
cors_origins = settings.BACKEND_CORS_ORIGINS if isinstance(settings.BACKEND_CORS_ORIGINS, list) else [settings.BACKEND_CORS_ORIGINS]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 Routers
app.include_router(health_router, prefix=settings.API_V1_STR)
app.include_router(system_router, prefix=settings.API_V1_STR)
app.include_router(connectors_router, prefix=settings.API_V1_STR)
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(resume_router, prefix=settings.API_V1_STR)
app.include_router(jobs_router, prefix=settings.API_V1_STR)
app.include_router(matching_router, prefix=settings.API_V1_STR)
app.include_router(applications_router, prefix=settings.API_V1_STR)
app.include_router(email_router, prefix=settings.API_V1_STR)
app.include_router(chat_router, prefix=settings.API_V1_STR)
app.include_router(integrations_router, prefix=settings.API_V1_STR)
app.include_router(analytics_router, prefix=settings.API_V1_STR)
app.include_router(mailbox_router, prefix=settings.API_V1_STR)
app.include_router(communication_router, prefix=settings.API_V1_STR)
app.include_router(interviews_router, prefix=settings.API_V1_STR)
app.include_router(settings_router, prefix=settings.API_V1_STR)
app.include_router(onboarding_router, prefix=settings.API_V1_STR)


@app.get("/api/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "ai_provider": settings.DEFAULT_AI_PROVIDER,
        "compliance_mode": "STRICT_NON_CIRCUMVENTION_ENFORCED"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)

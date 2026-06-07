from fastapi import FastAPI

from app.core.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    app = FastAPI(title=app_settings.app_name)

    @app.get(f"{app_settings.api_prefix}/health")
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "app_name": app_settings.app_name,
            "services": {
                "database_configured": bool(app_settings.database_url),
                "redis_configured": bool(app_settings.redis_url),
                "llm_configured": app_settings.llm_configured,
                "soffice_configured": app_settings.soffice_configured,
            },
        }

    return app


app = create_app()

from fastapi import FastAPI

from app.api.files import build_files_router
from app.core.config import Settings, get_settings
from app.storage.local import LocalFileStorage
from app.storage.repository import JsonMetadataRepository


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    app = FastAPI(title=app_settings.app_name)
    repository = JsonMetadataRepository(app_settings.file_storage_root / "metadata.json")
    file_storage = LocalFileStorage(app_settings.file_storage_root)

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

    app.include_router(build_files_router(repository, file_storage), prefix=app_settings.api_prefix)

    return app


app = create_app()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.extraction import ConfiguredLLMRuleExtractionProvider, ProfileExtractionService
from app.api.files import build_files_router
from app.api.jobs import build_jobs_router
from app.api.profile_extractions import build_profile_extractions_router
from app.api.profiles import build_profiles_router
from app.core.config import Settings, get_settings
from app.profiles.seed import load_builtin_profiles
from app.storage.local import LocalFileStorage
from app.storage.repository import JsonMetadataRepository


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    app = FastAPI(title=app_settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    repository = JsonMetadataRepository(app_settings.file_storage_root / "metadata.json")
    file_storage = LocalFileStorage(app_settings.file_storage_root)
    extraction_service = ProfileExtractionService(
        repository,
        app_settings.file_storage_root,
        app_settings.soffice_bin,
        ConfiguredLLMRuleExtractionProvider(app_settings),
    )
    for profile in load_builtin_profiles().values():
        if repository.get_profile_version(profile.id, profile.version) is None:
            repository.save_profile_version(profile)

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
    app.include_router(build_profiles_router(repository), prefix=app_settings.api_prefix)
    app.include_router(build_jobs_router(repository), prefix=app_settings.api_prefix)
    app.include_router(build_profile_extractions_router(extraction_service), prefix=app_settings.api_prefix)

    return app


app = create_app()

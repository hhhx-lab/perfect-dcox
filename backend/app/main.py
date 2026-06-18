from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.extraction import ConfiguredLLMRuleExtractionProvider, ProfileExtractionService
from app.agents.requirements import (
    OpenAICompatibleRequirementProvider,
    RequirementExtractionProvider,
    RequirementSessionService,
)
from app.api.batches import build_batches_router
from app.api.files import build_files_router
from app.api.jobs import build_jobs_router
from app.api.profile_extractions import build_profile_extractions_router
from app.api.profiles import build_profiles_router
from app.api.quality_reports import build_quality_reports_router
from app.api.requirement_sessions import build_requirement_sessions_router
from app.core.config import Settings, get_settings
from app.llm.diagnostics import check_llm_connectivity, unverified_llm_status
from app.profiles.seed import load_builtin_profiles
from app.quality.fix_execution import FixLoopExecutionService
from app.quality.final_layout_review import OpenAICompatibleFinalLayoutReviewer
from app.quality.service import QualityReportService
from app.storage.local import LocalFileStorage
from app.storage.repository import JsonMetadataRepository


def create_app(
    settings: Settings | None = None,
    requirement_provider: RequirementExtractionProvider | None = None,
) -> FastAPI:
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
    final_layout_reviewer = (
        OpenAICompatibleFinalLayoutReviewer(app_settings)
        if app_settings.llm_configured
        else None
    )
    extraction_service = ProfileExtractionService(
        repository,
        app_settings.file_storage_root,
        app_settings.soffice_bin,
        ConfiguredLLMRuleExtractionProvider(app_settings),
    )
    requirement_session_service = RequirementSessionService(
        repository,
        app_settings.file_storage_root,
        app_settings.soffice_bin,
        requirement_provider
        if requirement_provider is not None
        else OpenAICompatibleRequirementProvider(app_settings)
        if app_settings.llm_configured
        else None,
    )
    quality_report_service = QualityReportService(repository)
    fix_execution_service = FixLoopExecutionService(repository, file_storage, app_settings.soffice_bin)
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
                "llm_status": unverified_llm_status(app_settings),
                "soffice_configured": app_settings.soffice_configured,
            },
        }

    @app.get(f"{app_settings.api_prefix}/health/llm")
    def llm_health() -> dict[str, object]:
        return check_llm_connectivity(app_settings).to_dict()

    app.include_router(build_files_router(repository, file_storage), prefix=app_settings.api_prefix)
    app.include_router(build_profiles_router(repository), prefix=app_settings.api_prefix)
    app.include_router(
        build_jobs_router(
            repository,
            file_storage=file_storage,
            soffice_bin=app_settings.soffice_bin,
            final_layout_reviewer=final_layout_reviewer,
        ),
        prefix=app_settings.api_prefix,
    )
    app.include_router(
        build_batches_router(
            repository,
            file_storage=file_storage,
            soffice_bin=app_settings.soffice_bin,
            final_layout_reviewer=final_layout_reviewer,
        ),
        prefix=app_settings.api_prefix,
    )
    app.include_router(build_profile_extractions_router(extraction_service), prefix=app_settings.api_prefix)
    app.include_router(build_requirement_sessions_router(requirement_session_service), prefix=app_settings.api_prefix)
    app.include_router(
        build_quality_reports_router(quality_report_service, fix_execution_service=fix_execution_service),
        prefix=app_settings.api_prefix,
    )

    return app


app = create_app()

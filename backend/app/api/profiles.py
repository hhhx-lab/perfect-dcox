from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import ValidationError
from yaml import YAMLError

from app.profiles.models import FormatProfile, ProfileSummary
from app.profiles.seed import profile_to_yaml
from app.storage.repository import DuplicateProfileVersionError, JsonMetadataRepository


def profile_validation_error(error: ValidationError | YAMLError | ValueError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error))


def build_profiles_router(repository: JsonMetadataRepository) -> APIRouter:
    router = APIRouter(prefix="/profiles", tags=["profiles"])

    @router.get("", response_model=list[ProfileSummary])
    def list_profiles() -> list[ProfileSummary]:
        return sorted(repository.list_profiles(), key=lambda item: item.updated_at, reverse=True)

    @router.get("/{profile_id}/versions/{version}", response_model=FormatProfile)
    def get_profile_version(profile_id: str, version: str) -> FormatProfile:
        profile = repository.get_profile_version(profile_id, version)
        if profile is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile version not found.")
        return profile

    @router.post("", response_model=FormatProfile, status_code=status.HTTP_201_CREATED)
    def create_profile(payload: FormatProfile) -> FormatProfile:
        try:
            return repository.save_profile_version(payload)
        except DuplicateProfileVersionError as error:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error

    @router.post("/{profile_id}/versions", response_model=FormatProfile, status_code=status.HTTP_201_CREATED)
    def save_profile_version(profile_id: str, payload: FormatProfile) -> FormatProfile:
        if payload.id != profile_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profile id does not match URL.")
        try:
            return repository.save_profile_version(payload)
        except DuplicateProfileVersionError as error:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error

    @router.post("/{profile_id}/archive", response_model=ProfileSummary)
    def archive_profile(profile_id: str) -> ProfileSummary:
        archived = repository.archive_profile(profile_id)
        if archived is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
        return archived

    @router.post("/import", response_model=FormatProfile, status_code=status.HTTP_201_CREATED)
    async def import_profile(request: Request) -> FormatProfile:
        import yaml

        body = (await request.body()).decode("utf-8")
        try:
            raw = yaml.safe_load(body)
            profile = FormatProfile.model_validate(raw)
            return repository.save_profile_version(profile)
        except DuplicateProfileVersionError as error:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
        except (ValidationError, YAMLError, ValueError) as error:
            raise profile_validation_error(error) from error

    @router.get("/{profile_id}/versions/{version}/export")
    def export_profile(profile_id: str, version: str) -> Response:
        profile = repository.get_profile_version(profile_id, version)
        if profile is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile version not found.")
        return Response(content=profile_to_yaml(profile), media_type="application/x-yaml; charset=utf-8")

    return router

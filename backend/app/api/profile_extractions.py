from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.agents.extraction import ExtractionSourceError, ProfileExtractionService
from app.models import ExtractionSourceType, ProfileExtractionRecord


class CreateProfileExtractionRequest(BaseModel):
    source_type: ExtractionSourceType
    file_id: str | None = None
    natural_language: str | None = None


def build_profile_extractions_router(
    service: ProfileExtractionService,
) -> APIRouter:
    router = APIRouter(prefix="/profile-extractions", tags=["profile-extractions"])

    @router.post("", response_model=ProfileExtractionRecord, status_code=status.HTTP_201_CREATED)
    def create_profile_extraction(payload: CreateProfileExtractionRequest) -> ProfileExtractionRecord:
        if payload.source_type == "document" and not payload.file_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="file_id is required for document extraction.")
        if payload.source_type == "natural_language" and payload.file_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="file_id is not allowed for natural_language extraction.",
            )
        try:
            return service.create_extraction(payload.file_id, payload.natural_language)
        except ExtractionSourceError as error:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    return router

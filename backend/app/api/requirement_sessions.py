from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.agents.extraction import ExtractionSourceError
from app.agents.requirements import RequirementSessionService
from app.models import RequirementAttachmentSourceKind, RequirementSession, RequirementSessionAttachment, RequirementSessionSourceType
from app.profiles.models import FormatProfile


class RequirementAttachmentInput(BaseModel):
    file_id: str | None = None
    source_kind: RequirementAttachmentSourceKind
    filename: str | None = None


class CreateRequirementSessionRequest(BaseModel):
    source_type: RequirementSessionSourceType
    natural_language: str | None = None
    file_id: str | None = None
    attachments: list[RequirementAttachmentInput] = Field(default_factory=list)
    current_profile: FormatProfile | None = None
    locked_fields: list[str] = Field(default_factory=list)


class AddRequirementMessageRequest(BaseModel):
    content: str = Field(min_length=1)
    current_profile: FormatProfile | None = None
    locked_fields: list[str] = Field(default_factory=list)


class AddRequirementAttachmentRequest(BaseModel):
    file_id: str
    source_kind: RequirementAttachmentSourceKind
    filename: str | None = None
    current_profile: FormatProfile | None = None
    locked_fields: list[str] = Field(default_factory=list)


class ConfirmRequirementSessionRequest(BaseModel):
    profile_name: str = Field(min_length=1)
    profile_version: str = "1.0.0"
    profile_description: str | None = None


def build_requirement_sessions_router(service: RequirementSessionService) -> APIRouter:
    router = APIRouter(prefix="/requirement-sessions", tags=["requirement-sessions"])

    @router.post("", response_model=RequirementSession, status_code=status.HTTP_201_CREATED)
    def create_requirement_session(payload: CreateRequirementSessionRequest) -> RequirementSession:
        try:
            return service.create_session(
                payload.source_type,
                natural_language=payload.natural_language,
                file_id=payload.file_id,
                attachments=[RequirementSessionAttachment(**item.model_dump()) for item in payload.attachments],
                current_profile=payload.current_profile,
                locked_fields=payload.locked_fields,
            )
        except ExtractionSourceError as error:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    @router.get("/{session_id}", response_model=RequirementSession)
    def get_requirement_session(session_id: str) -> RequirementSession:
        session = service.repository.get_requirement_session(session_id)
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirement session not found.")
        return session

    @router.post("/{session_id}/messages", response_model=RequirementSession)
    def add_requirement_message(session_id: str, payload: AddRequirementMessageRequest) -> RequirementSession:
        try:
            return service.add_message(
                session_id,
                payload.content,
                current_profile=payload.current_profile,
                locked_fields=payload.locked_fields,
            )
        except ExtractionSourceError as error:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    @router.post("/{session_id}/attachments", response_model=RequirementSession)
    def add_requirement_attachment(session_id: str, payload: AddRequirementAttachmentRequest) -> RequirementSession:
        try:
            return service.add_attachment(
                session_id,
                RequirementSessionAttachment(
                    file_id=payload.file_id,
                    source_kind=payload.source_kind,
                    filename=payload.filename,
                ),
                current_profile=payload.current_profile,
                locked_fields=payload.locked_fields,
            )
        except ExtractionSourceError as error:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    @router.post("/{session_id}/confirm", response_model=RequirementSession)
    def confirm_requirement_session(session_id: str, payload: ConfirmRequirementSessionRequest) -> RequirementSession:
        try:
            return service.confirm_session(
                session_id,
                profile_name=payload.profile_name,
                profile_version=payload.profile_version,
                profile_description=payload.profile_description,
            )
        except ExtractionSourceError as error:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    return router

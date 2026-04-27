"""Pydantic schemas for ``ModuleContent.content_data``.

One schema per ``ModuleContent.ContentType``. The validator dispatches by
``content_type`` and rejects payloads that don't match the canonical
shape — the class of bug that produced the silent quiz mismatch (seed
wrote ``{q, choices, answer}``; viewer expected ``{text, options,
correct_answer}``; nothing checked).

The legacy hand-rolled validator in ``learning.models`` only verified
top-level keys; it accepted "anything with a ``questions`` list", which
is why the bug slipped past. Pydantic enforces every leaf field.

This module raises Pydantic's native ``ValidationError`` (re-exported as
``ContentSchemaError`` so call sites don't need to import pydantic).
The two call sites — ``ModuleContent.clean()`` and the DRF
``ModuleContentCreateSerializer.validate_content_data()`` — wrap that
in their respective ValidationError types so each side surfaces errors
in the form its caller expects.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, ValidationError as ContentSchemaError


# ---------------------------------------------------------------------------
# Quiz — the schema the QuizBuilder authoring component writes and the
# QuizTaker viewer reads. Aligned with
# ``frontend/src/components/custom/QuizBuilder.tsx::QuizQuestion``.
# ---------------------------------------------------------------------------


class QuizOption(BaseModel):
    """A single answer option inside a quiz question.

    ``id`` is opaque (UUID or stable client-generated key); ``isCorrect``
    is the per-option correctness flag the viewer reads when scoring.
    """

    id: str = Field(min_length=1)
    text: str
    isCorrect: bool


class QuizQuestion(BaseModel):
    """One question. Single-choice or multi-select."""

    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    type: Literal['single', 'multiple']
    options: list[QuizOption] = Field(min_length=2)
    points: int = Field(ge=0, default=10)


class QuizContentData(BaseModel):
    """Top-level shape persisted under ``content_data`` for quiz content."""

    questions: list[QuizQuestion] = Field(min_length=1)
    passing_score: int = Field(ge=0, le=100, default=70)


# ---------------------------------------------------------------------------
# Text / video / external / lesson / document schemas
# ---------------------------------------------------------------------------


class TextContentData(BaseModel):
    """Rich-text body. ``body`` is HTML emitted by the rich text editor."""

    body: str


class VideoContentData(BaseModel):
    """Streaming or hosted-video URL plus optional metadata."""

    url: str = Field(min_length=1)
    provider: str | None = None
    thumbnail: str | None = None


class ExternalContentData(BaseModel):
    """External link surfaced as a content item.

    Default of ``open_in_new_tab=True`` matches the seed and the typical
    learner expectation for outbound links.
    """

    url: str = Field(min_length=1)
    open_in_new_tab: bool = True


class LessonVideo(BaseModel):
    url: str = Field(min_length=1)


class LessonText(BaseModel):
    body: str


class LessonContentData(BaseModel):
    """Composite "video + accompanying notes" content. Both halves optional —
    seed sometimes uses one, sometimes the other, sometimes both."""

    video: LessonVideo | None = None
    text: LessonText | None = None


class DocumentContentData(BaseModel):
    """Documents have no JSON payload — the binary lives on
    ``ModuleContent.file``. This schema is permissive (extra keys
    allowed) so legacy authoring data with no payload still passes."""

    model_config = {'extra': 'allow'}


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


# Tuple keyed by ContentType.value → schema class. Add a new content_type
# to the enum AND to this map; tests for ``validate_content_data`` will
# fail if either side is missed.
CONTENT_TYPE_SCHEMAS: dict[str, type[BaseModel]] = {
    'text': TextContentData,
    'video': VideoContentData,
    'document': DocumentContentData,
    'quiz': QuizContentData,
    'lesson': LessonContentData,
    'external': ExternalContentData,
}


def validate_content_data(content_type: str, content_data) -> None:
    """Strict per-content_type validation.

    Raises ``ContentSchemaError`` (re-export of pydantic's ValidationError)
    on failure. Call sites wrap that in the appropriate framework error
    type — Django's ``ValidationError`` from ``Model.clean()``, DRF's
    ``ValidationError`` from a serializer's ``validate_*``.

    Empty / null payloads are accepted (legacy seed leaves them blank for
    document content and similar). Anything non-empty must match the
    canonical schema for its content_type.
    """
    if content_data is None or content_data == {}:
        return
    if not isinstance(content_data, dict):
        # Synthetic Pydantic-shaped error so call sites' format helpers work uniformly.
        raise ContentSchemaError.from_exception_data(
            'content_data',
            [{'type': 'dict_type', 'loc': (), 'input': content_data}],
        )

    schema = CONTENT_TYPE_SCHEMAS.get(content_type)
    if schema is None:
        raise ContentSchemaError.from_exception_data(
            'content_data',
            [{'type': 'literal_error', 'loc': ('content_type',), 'input': content_type,
              'ctx': {'expected': ', '.join(CONTENT_TYPE_SCHEMAS.keys())}}],
        )

    schema.model_validate(content_data)


def format_schema_error(exc: ContentSchemaError) -> dict[str, str]:
    """Flatten a Pydantic error into ``{"field.path": "message", …}``.

    Both call sites use this to produce a form-friendly error blob. The
    frontend's ``formErrorsFromApi`` reads the same shape regardless of
    which side raised.
    """
    out: dict[str, str] = {}
    for err in exc.errors():
        path = '.'.join(str(p) for p in err['loc']) or 'content_data'
        out[path] = err['msg']
    return out

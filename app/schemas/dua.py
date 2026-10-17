from pydantic import BaseModel, Field


class DuaSummaryResponse(BaseModel):
    id: str
    title: str
    category: str
    source_reference: str | None = None
    source: str


class DuaResponse(DuaSummaryResponse):
    arabic: str
    transliteration: str | None = None
    translation: str
    references: list[dict | str] = Field(default_factory=list)
    audio_url: str | None = None
    source_url: str

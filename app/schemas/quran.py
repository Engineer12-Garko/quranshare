from pydantic import BaseModel


class VerseOfDayResponse(BaseModel):
    date: str
    verse_key: str
    arabic: str
    translation: str
    translation_source: str | None = None
    source: str

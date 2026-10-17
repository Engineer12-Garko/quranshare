from pydantic import BaseModel


class ChapterResponse(BaseModel):
    id: int
    name_simple: str
    name_arabic: str
    name_complex: str | None = None
    translated_name: str | None = None
    verses_count: int
    revelation_place: str | None = None


class VerseResponse(BaseModel):
    verse_key: str
    chapter_id: int
    verse_number: int
    chapter_name: str | None = None
    chapter_name_arabic: str | None = None
    arabic: str
    translation: str
    translation_source: str | None = None
    translation_resource_id: int | str | None = None
    juz_number: int | None = None
    hizb_number: int | None = None
    page_number: int | None = None
    ruku_number: int | None = None
    manzil_number: int | None = None
    source: str


class PaginationResponse(BaseModel):
    current_page: int
    next_page: int | None = None
    total_pages: int
    total_records: int


class ChapterVersesResponse(BaseModel):
    chapter: ChapterResponse
    verses: list[VerseResponse]
    pagination: PaginationResponse


class VerseOfDayResponse(VerseResponse):
    date: str


class LiveVerseResponse(VerseResponse):
    audio_url: str | None = None


class LiveChapterVersesResponse(BaseModel):
    chapter: ChapterResponse
    verses: list[LiveVerseResponse]
    translation_edition: str

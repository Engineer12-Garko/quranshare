"""Pydantic schemas for weekly progress response."""
from pydantic import BaseModel


class DayProgress(BaseModel):
    date: str          # ISO date string YYYY-MM-DD
    posted: bool
    count: int         # number of videos posted that day


class WeeklyProgressResponse(BaseModel):
    week_start: str    # ISO date of Monday
    week_end: str      # ISO date of Sunday
    days: list[DayProgress]
    total_posted: int
    goal: int          # always 7 for V1

"""Tests for deterministic daily reminder rotation."""
from datetime import date, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.user import User
from app.models.video import Video
from app.models.posting_history import PostingHistory
from app.services.reminder import get_today_reminder
from app.utils.security import hash_password


@pytest.fixture
def db_session():
    """Create a fresh in-memory database for each test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        email="rotation@test.com",
        password_hash=hash_password("Secret123"),
        display_name="Rotation Test",
        role="user",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def active_videos(db_session):
    """Create 5 active videos."""
    videos = []
    for i in range(5):
        video = Video(
            drive_file_id=f"drive-{i}",
            title=f"Video {i}",
            is_active=True,
        )
        db_session.add(video)
        videos.append(video)
    db_session.commit()
    for v in videos:
        db_session.refresh(v)
    return videos


class TestDailyRotation:
    """Test deterministic daily rotation of reminders."""

    def test_same_user_same_date_same_video(self, db_session, test_user, active_videos):
        """Same user + same date = same recommendation."""
        with patch("app.services.reminder.date") as mock_date:
            mock_date.today.return_value = date(2026, 9, 29)
            mock_date.fromordinal = date.fromordinal

            result1 = get_today_reminder(db_session, test_user.id)
            result2 = get_today_reminder(db_session, test_user.id)

            assert result1.id == result2.id

    def test_different_date_different_video(self, db_session, test_user, active_videos):
        """Different date = normally different recommendation."""
        with patch("app.services.reminder.date") as mock_date:
            mock_date.today.return_value = date(2026, 9, 29)
            mock_date.fromordinal = date.fromordinal
            result_day1 = get_today_reminder(db_session, test_user.id)

            mock_date.today.return_value = date(2026, 9, 30)
            result_day2 = get_today_reminder(db_session, test_user.id)

            # With 5 videos, consecutive days should (almost certainly) differ
            assert result_day1.id != result_day2.id

    def test_rotation_with_three_videos(self, db_session, test_user):
        """Three videos should rotate over successive days."""
        videos = []
        for i in range(3):
            v = Video(drive_file_id=f"rot-{i}", title=f"Rot {i}", is_active=True)
            db_session.add(v)
            videos.append(v)
        db_session.commit()
        for v in videos:
            db_session.refresh(v)

        results = []
        base_date = date(2026, 9, 29)
        for day_offset in range(3):
            with patch("app.services.reminder.date") as mock_date:
                mock_date.today.return_value = base_date + timedelta(days=day_offset)
                mock_date.fromordinal = date.fromordinal
                result = get_today_reminder(db_session, test_user.id)
                results.append(result.id)

        # All three days should produce different videos
        assert len(set(results)) == 3

    def test_single_video_same_result(self, db_session, test_user):
        """Only one active video = same result regardless of date."""
        v = Video(drive_file_id="only-1", title="Only Video", is_active=True)
        db_session.add(v)
        db_session.commit()
        db_session.refresh(v)

        with patch("app.services.reminder.date") as mock_date:
            mock_date.today.return_value = date(2026, 9, 29)
            mock_date.fromordinal = date.fromordinal
            result1 = get_today_reminder(db_session, test_user.id)

            mock_date.today.return_value = date(2026, 9, 30)
            result2 = get_today_reminder(db_session, test_user.id)

            assert result1.id == result2.id == v.id

    def test_recently_posted_excluded(self, db_session, test_user, active_videos):
        """Recently posted videos should be excluded."""
        # Mark video 0 as posted today
        posted = PostingHistory(
            user_id=test_user.id,
            video_id=active_videos[0].id,
            action="posted",
        )
        db_session.add(posted)
        db_session.commit()

        with patch("app.services.reminder.date") as mock_date:
            mock_date.today.return_value = date(2026, 9, 29)
            mock_date.fromordinal = date.fromordinal
            result = get_today_reminder(db_session, test_user.id)

            # The recently posted video should not be selected
            assert result.id != active_videos[0].id

    def test_different_users_different_recommendations(
        self, db_session, active_videos
    ):
        """Different users should get different recommendations on the same day."""
        user1 = User(
            email="user1@test.com",
            password_hash=hash_password("Secret123"),
            display_name="User 1",
            role="user",
            is_active=True,
        )
        user2 = User(
            email="user2@test.com",
            password_hash=hash_password("Secret123"),
            display_name="User 2",
            role="user",
            is_active=True,
        )
        db_session.add(user1)
        db_session.add(user2)
        db_session.commit()
        db_session.refresh(user1)
        db_session.refresh(user2)

        with patch("app.services.reminder.date") as mock_date:
            mock_date.today.return_value = date(2026, 9, 29)
            mock_date.fromordinal = date.fromordinal

            result1 = get_today_reminder(db_session, user1.id)
            result2 = get_today_reminder(db_session, user2.id)

            # Different users should (almost certainly) get different videos
            assert result1.id != result2.id

    def test_date_transition_changes_recommendation(
        self, db_session, test_user, active_videos
    ):
        """Recommendation should change when date changes."""
        with patch("app.services.reminder.date") as mock_date:
            mock_date.today.return_value = date(2026, 9, 29)
            mock_date.fromordinal = date.fromordinal
            day1_result = get_today_reminder(db_session, test_user.id)

            mock_date.today.return_value = date(2026, 9, 30)
            day2_result = get_today_reminder(db_session, test_user.id)

            assert day1_result.id != day2_result.id

    def test_refresh_same_day_stable(self, db_session, test_user, active_videos):
        """Refreshing on the same day should return the same video."""
        with patch("app.services.reminder.date") as mock_date:
            mock_date.today.return_value = date(2026, 9, 29)
            mock_date.fromordinal = date.fromordinal

            results = [
                get_today_reminder(db_session, test_user.id).id for _ in range(10)
            ]

            assert len(set(results)) == 1

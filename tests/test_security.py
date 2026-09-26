"""
Tests for the password hashing utilities in app/utils/security.py
"""
from app.utils.security import hash_password, verify_password


def test_hash_is_not_plaintext():
    hashed = hash_password("mySecret123")
    assert hashed != "mySecret123"


def test_correct_password_verifies():
    hashed = hash_password("mySecret123")
    assert verify_password("mySecret123", hashed) is True


def test_wrong_password_fails():
    hashed = hash_password("mySecret123")
    assert verify_password("wrongPassword", hashed) is False


def test_empty_password_does_not_match_non_empty_hash():
    hashed = hash_password("mySecret123")
    assert verify_password("", hashed) is False


def test_different_hashes_for_same_password():
    """Argon2id should produce unique salts each time."""
    h1 = hash_password("mySecret123")
    h2 = hash_password("mySecret123")
    assert h1 != h2
    # But both still verify
    assert verify_password("mySecret123", h1) is True
    assert verify_password("mySecret123", h2) is True

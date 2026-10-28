from datetime import timedelta

from django.conf import settings


def test_jwt_lifetimes_match_session_policy():
    assert settings.NINJA_JWT["ACCESS_TOKEN_LIFETIME"] == timedelta(hours=12)
    assert settings.NINJA_JWT["REFRESH_TOKEN_LIFETIME"] == timedelta(days=30)


def test_jwt_rotation_and_blacklist_remain_enabled():
    assert settings.NINJA_JWT["ROTATE_REFRESH_TOKENS"] is True
    assert settings.NINJA_JWT["BLACKLIST_AFTER_ROTATION"] is True
    assert "ninja_jwt.token_blacklist" in settings.INSTALLED_APPS

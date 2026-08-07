"""Tests for security utilities — pure functions, no infrastructure."""

import os
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://t:t@localhost/t")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("GITHUB_APP_ID", "1")
os.environ.setdefault("GITHUB_PRIVATE_KEY", "dGVzdA==")
os.environ.setdefault("GITHUB_WEBHOOK_SECRET", "s")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key-that-is-32-chars!!")

from app.utils.security import (
    generate_license_key,
    generate_relay_secret,
    hash_key,
    verify_key,
)


class TestGenerateLicenseKey:
    def test_starts_with_prefix(self):
        assert generate_license_key().startswith("aeth_")

    def test_minimum_length(self):
        # "aeth_" + 48 URL-safe chars ≥ 53 chars total
        assert len(generate_license_key()) >= 53

    def test_unique_each_call(self):
        keys = {generate_license_key() for _ in range(100)}
        assert len(keys) == 100


class TestHashKey:
    def test_returns_64_hex_chars(self):
        h = hash_key("aeth_somekey")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_deterministic(self):
        assert hash_key("same") == hash_key("same")

    def test_different_inputs_differ(self):
        assert hash_key("key-a") != hash_key("key-b")


class TestVerifyKey:
    def test_correct_key_returns_true(self):
        key = generate_license_key()
        stored = hash_key(key)
        assert verify_key(key, stored) is True

    def test_wrong_key_returns_false(self):
        key = generate_license_key()
        stored = hash_key(key)
        assert verify_key("aeth_wrongkey", stored) is False

    def test_empty_key_returns_false(self):
        stored = hash_key("aeth_real")
        assert verify_key("", stored) is False


class TestGenerateRelaySecret:
    def test_minimum_length(self):
        assert len(generate_relay_secret()) >= 40

    def test_unique(self):
        secrets = {generate_relay_secret() for _ in range(50)}
        assert len(secrets) == 50

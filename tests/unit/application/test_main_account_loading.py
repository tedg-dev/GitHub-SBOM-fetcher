"""Tests for account-based token loading in main.py."""

import tempfile
from pathlib import Path

import pytest

from sbom_fetcher.application.main import load_token
from sbom_fetcher.domain.exceptions import TokenLoadError


class TestAccountBasedTokenLoading:
    """Test account-based token loading from keys file."""

    def test_load_token_with_valid_account(self):
        """Test loading token for a specific account."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(
                """{
                "accounts": [
                    {"username": "alice", "token": "ghp_alice123"},
                    {"username": "bob", "token": "ghp_bob456"}
                ]
            }"""
            )
            key_file = f.name

        try:
            token = load_token(key_file, account="bob")
            assert token == "ghp_bob456"
        finally:
            Path(key_file).unlink()

    def test_load_token_account_without_token(self):
        """Test loading account that exists but has no token."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(
                """{
                "accounts": [
                    {"username": "alice", "token": "ghp_alice123"},
                    {"username": "bob"}
                ]
            }"""
            )
            key_file = f.name

        try:
            with pytest.raises(TokenLoadError, match="Account 'bob' found but has no token"):
                load_token(key_file, account="bob")
        finally:
            Path(key_file).unlink()

    def test_load_token_account_with_null_token(self):
        """Test loading account with null token value."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(
                """{
                "accounts": [
                    {"username": "alice", "token": null}
                ]
            }"""
            )
            key_file = f.name

        try:
            with pytest.raises(TokenLoadError, match="Account 'alice' found but has no token"):
                load_token(key_file, account="alice")
        finally:
            Path(key_file).unlink()

    def test_load_token_account_not_found(self):
        """Test loading non-existent account."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(
                """{
                "accounts": [
                    {"username": "alice", "token": "ghp_alice123"},
                    {"username": "bob", "token": "ghp_bob456"}
                ]
            }"""
            )
            key_file = f.name

        try:
            with pytest.raises(
                TokenLoadError,
                match="Account 'charlie' not found in keys file. Available accounts: alice, bob",
            ):
                load_token(key_file, account="charlie")
        finally:
            Path(key_file).unlink()

    def test_load_token_account_not_found_no_accounts(self):
        """Test loading account when accounts array is empty."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"accounts": []}')
            key_file = f.name

        try:
            with pytest.raises(
                TokenLoadError,
                match="Account 'alice' not found in keys file. Available accounts: none",
            ):
                load_token(key_file, account="alice")
        finally:
            Path(key_file).unlink()

    def test_load_token_account_not_found_accounts_without_username(self):
        """Test loading account when some accounts lack username field."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(
                """{
                "accounts": [
                    {"token": "ghp_nouser123"},
                    {"username": "bob", "token": "ghp_bob456"}
                ]
            }"""
            )
            key_file = f.name

        try:
            with pytest.raises(
                TokenLoadError,
                match="Account 'alice' not found in keys file. Available accounts: bob",
            ):
                load_token(key_file, account="alice")
        finally:
            Path(key_file).unlink()

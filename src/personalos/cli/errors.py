"""Shared CLI error type used across every cli/ submodule."""

from __future__ import annotations


class CliError(RuntimeError):
    """Raised for expected fail-closed CLI errors."""

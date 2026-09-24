#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Global test configuration for martpy tests."""

from pathlib import Path

import pytest

# Global temporary outputs directory for manual verification
# This directory persists after tests, allowing inspection of written files
# (useful for debugging or manual verification ; please do not change to
# pytest.tmp_path() which lives only during tests session).
TMP_OUTPUTS_DIR = Path("tests/tmp_outputs")


# Ensure the directory exists
def _ensure_tmp_outputs_exists():
    TMP_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


# Pytest fixture that ensures the directory exists
# Can be used in tests that need the directory to exist
@pytest.fixture(scope="session", autouse=True)
def ensure_tmp_outputs_dir():
    """Ensure tmp_outputs directory exists before any tests run."""
    _ensure_tmp_outputs_exists()
    return TMP_OUTPUTS_DIR

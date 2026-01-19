"""
Pytest runner for Django's manage.py test command.
"""

from __future__ import annotations

import os
from typing import Sequence

from django.test.runner import DiscoverRunner


class PytestTestRunner(DiscoverRunner):
    """Delegate test execution to pytest."""

    def run_tests(self, test_labels: Sequence[str], extra_tests=None, **kwargs):  # type: ignore[override]
        import pytest

        # Ensure pytest sees the test settings module.
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")

        args = list(test_labels) if test_labels else []
        return pytest.main(args)

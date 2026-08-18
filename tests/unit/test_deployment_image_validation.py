"""Unit tests for production-image release-gate behavior."""

from types import SimpleNamespace

import pytest

from tests.scenarios.test_deployment_scenarios import _ensure_production_image


def test_supplied_production_image_validation_failure_is_not_skipped(monkeypatch):
    monkeypatch.setenv("RMCP_PRODUCTION_IMAGE", "rmcp:test")
    monkeypatch.setattr("shutil.which", lambda command: "/usr/bin/docker")
    results = iter(
        [
            SimpleNamespace(returncode=0, stdout=b"", stderr=b""),
            SimpleNamespace(returncode=1, stdout="", stderr="missing dependency"),
        ]
    )
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: next(results))

    with pytest.raises(AssertionError, match="missing required dependencies"):
        _ensure_production_image()

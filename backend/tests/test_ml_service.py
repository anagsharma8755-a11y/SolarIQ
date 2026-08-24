from __future__ import annotations

from typing import Any

import pytest

from backend.services.ml_service import MLService


class _MockModel:
    """Simple mock model for testing the ML adapter."""

    def predict(
        self,
        features: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "predicted_score": 0.85,
            "confidence": 0.9,
        }


class _BadModel:
    """Mock model that returns invalid output."""

    def predict(
        self,
        features: dict[str, Any],
    ) -> str:
        return "not_a_dict"


def test_ml_service_not_available_by_default():
    service = MLService()

    assert service.available is False


def test_ml_service_available_with_model():
    service = MLService(model=_MockModel())

    assert service.available is True


def test_ml_service_predict_raises_without_model():
    service = MLService()

    with pytest.raises(RuntimeError, match="not connected"):
        service.predict({"area_m2": 100.0})


def test_ml_service_predict_if_available_returns_none():
    service = MLService()

    result = service.predict_if_available(
        {"area_m2": 100.0}
    )

    assert result is None


def test_ml_service_predict_with_mock_model():
    service = MLService(model=_MockModel())

    result = service.predict({"area_m2": 100.0})

    assert result == {
        "predicted_score": 0.85,
        "confidence": 0.9,
    }


def test_ml_service_predict_if_available_with_model():
    service = MLService(model=_MockModel())

    result = service.predict_if_available(
        {"area_m2": 100.0}
    )

    assert result is not None
    assert result["predicted_score"] == 0.85


def test_ml_service_predict_invalid_result():
    service = MLService(model=_BadModel())

    with pytest.raises(ValueError, match="dictionary"):
        service.predict({"area_m2": 100.0})

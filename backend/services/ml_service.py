from __future__ import annotations

from typing import Any, Protocol


class SolarPredictionModel(Protocol):
    """
    Interface expected from Person 1's ML model.

    Person 1 can implement this interface without
    changing the FastAPI layer.
    """

    def predict(
        self,
        features: dict[str, Any],
    ) -> dict[str, Any]:
        ...


class MLService:
    """
    Adapter between the backend and Person 1's ML model.

    Until the actual ML model is available, the service
    safely reports that ML prediction is unavailable.

    The geometry and fallback solar calculations continue
    to work independently.
    """

    def __init__(
        self,
        model: SolarPredictionModel | None = None,
    ) -> None:
        self.model = model

    @property
    def available(self) -> bool:
        """Return whether an ML model is connected."""
        return self.model is not None

    def predict(
        self,
        features: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Run the connected ML model.

        Raises:
            RuntimeError: if no ML model is connected.
        """

        if self.model is None:
            raise RuntimeError(
                "Solar ML model is not connected."
            )

        result = self.model.predict(
            features
        )

        if not isinstance(result, dict):
            raise ValueError(
                "ML model prediction must return a dictionary."
            )

        return result

    def predict_if_available(
        self,
        features: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Run ML prediction only when a model is available.

        Returns None when the ML model has not yet
        been integrated.
        """

        if not self.available:
            return None

        return self.predict(features)


ml_service = MLService()
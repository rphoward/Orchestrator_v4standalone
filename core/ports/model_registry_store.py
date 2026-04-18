from __future__ import annotations

import abc

from orchestrator_v4.core.entities.model_registry_entry import ModelRegistryEntry


class ModelRegistryStore(abc.ABC):
    """Read and write the model registry and router-model config."""

    @abc.abstractmethod
    def get_models(self) -> list[ModelRegistryEntry]:
        """Return all models in the registry."""

    @abc.abstractmethod
    def save_models(self, models: list[ModelRegistryEntry]) -> None:
        """Replace the entire model registry."""

    @abc.abstractmethod
    def get_router_model(self) -> str:
        """Return the current router model id."""

    @abc.abstractmethod
    def set_router_model(self, model_id: str) -> None:
        """Set the router model id."""

    @abc.abstractmethod
    def get_default_active_model_id(self) -> str:
        """First active model id in the registry; fallback when agent model is unset."""

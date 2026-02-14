"""Component-specific log collectors."""

from typing import Dict, Type

from host_logging.collectors.imp import IMPCollector
from host_logging.collectors.vax import VAXCollector
from host_logging.core.collector import BaseCollector

# Default collector registry
# Maps component names to their collector classes
DEFAULT_COLLECTOR_REGISTRY: Dict[str, Type[BaseCollector]] = {
    "vax": VAXCollector,
    "imp1": IMPCollector,
    "imp2": IMPCollector,
    "pdp10": IMPCollector,  # Can be extended with PDP10Collector later
}


def get_collector_class(component: str) -> Type[BaseCollector]:
    """Get collector class for a component.

    Args:
        component: Component name (e.g., "vax", "imp1", "pdp10")

    Returns:
        Collector class for the component

    Raises:
        ValueError: If no collector is registered for the component

    Example:
        >>> collector_class = get_collector_class("vax")
        >>> collector = collector_class(
        ...     build_id="build-123",
        ...     container_name="arpanet-vax",
        ...     storage=storage
        ... )
    """
    if component not in DEFAULT_COLLECTOR_REGISTRY:
        raise ValueError(
            f"No collector registered for component '{component}'. "
            f"Available: {', '.join(DEFAULT_COLLECTOR_REGISTRY.keys())}"
        )
    return DEFAULT_COLLECTOR_REGISTRY[component]


__all__ = [
    "VAXCollector",
    "IMPCollector",
    "DEFAULT_COLLECTOR_REGISTRY",
    "get_collector_class",
]

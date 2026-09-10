# Day-15 workload registry (family -> implementation class).
# Imported by scripts/run_workload.py, scripts/validate_workloads.py, tests.
# Kept as a data file (not a package __init__) so importing the registry
# never executes workload code as a side effect.
from sparkrl.workloads.base import FAMILIES, BaseWorkload
from sparkrl.workloads.families import (
    F1Aggregation,
    F2Join,
    F3Rdd,
    F4SkewJoin,
    F5Mixed,
)

REGISTRY: dict[str, type[BaseWorkload]] = {
    "F1_agg": F1Aggregation,
    "F2_join": F2Join,
    "F3_rdd": F3Rdd,
    "F4_ski": F4SkewJoin,
    "F5_mixed": F5Mixed,
}

VERSIONS: dict[str, str] = {
    family: cls.workload_version for family, cls in REGISTRY.items()
}


def get_workload(family: str, scale: str, seed: int) -> BaseWorkload:
    """Instantiate the registered workload for (family, scale, seed)."""
    try:
        cls = REGISTRY[family]
    except KeyError:
        raise ValueError(
            f"unknown family {family!r}; expected one of {list(REGISTRY)}"
        ) from None
    return cls(scale=scale, seed=seed)


__all__ = ["FAMILIES", "REGISTRY", "VERSIONS", "get_workload"]

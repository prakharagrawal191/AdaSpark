"""Deterministic Zipf/skew sampling, pure stdlib (Day 13).

Semantics: Zipf(s, K) over keys 0..K-1 with P(key=k) proportional to
1/(k+1)^s. s=0 is uniform (handled without a CDF table). Larger s puts
more mass on low keys: s=0.5 mild skew, s=1.0 classic Zipf (top key ~10x
the median key's mass at K=1000), s=1.5 extreme skew.

Determinism: draws come from a caller-owned random.Random instance; the
sampler holds no RNG state. Same (seed, s, K, draw order) => same keys.
"""
from __future__ import annotations

import bisect
import random

# CDF is a pure function of (key_cardinality, skew). Day-14: build once and
# reuse across rows/datasets — avoids O(K*N) rebuilds in replay-validated
# samplers (critical at K=750k..7.5M, e.g. full_validation's row sampler).
_CDF_CACHE: dict[tuple[int, float], tuple[list[float], float]] = {}


def _build_cdf(key_cardinality: int, skew: float) -> tuple[list[float], float]:
    """Canonical cumulative distribution for Zipf(s, K) with s > 0.

    Returns (cdf, total) where cdf[-1] == 1.0 (float error absorbed). The
    result is cached globally because it depends only on (K, s).
    """
    key = (key_cardinality, skew)
    hit = _CDF_CACHE.get(key)
    if hit is not None:
        return hit
    total = sum((k + 1) ** -skew for k in range(key_cardinality))
    cumulative = 0.0
    cdf: list[float] = [0.0] * key_cardinality
    for k in range(key_cardinality):
        cumulative += ((k + 1) ** -skew) / total
        cdf[k] = cumulative
    cdf[-1] = 1.0  # absorb float error so bisect never overruns
    _CDF_CACHE[key] = (cdf, total)
    return (cdf, total)


class ZipfSampler:
    """Precomputed-CDF Zipf sampler over a bounded key domain."""

    def __init__(self, key_cardinality: int, skew: float) -> None:
        if not isinstance(key_cardinality, int) or key_cardinality < 1:
            raise ValueError(
                f"key_cardinality must be a positive int, got {key_cardinality!r}")
        if not isinstance(skew, (int, float)) or skew < 0:
            raise ValueError(f"skew must be a number >= 0, got {skew!r}")
        if skew > 5.0:
            raise ValueError(f"skew > 5.0 is unsupported (got {skew!r})")
        self.key_cardinality = int(key_cardinality)
        self.skew = float(skew)
        self._cdf: list[float] | None = None
        if self.skew > 0:
            self._cdf = _build_cdf(self.key_cardinality, self.skew)[0]

    def sample(self, rng: random.Random) -> int:
        """Draw one key in [0, K) using the caller's RNG (uniform if s=0)."""
        if self._cdf is None:
            return rng.randrange(self.key_cardinality)
        return bisect.bisect_left(self._cdf, rng.random())

    @property
    def top_key_mass(self) -> float:
        """P(key=0); useful for documenting/skew-sanity checks."""
        if self._cdf is None:
            return 1.0 / self.key_cardinality
        return self._cdf[0]

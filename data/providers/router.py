"""Provider fallback router for evidence data.

The router makes data-source replacement cheap.  A future direct Eastmoney or
InStock-compatible provider can be added ahead of/behind AKShare without
touching the four strategies.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass
class RoutedResult:
    data: Any
    source: str


class ProviderRouter:
    def __init__(self, providers: Iterable[Any]):
        self.providers = list(providers)

    def call(self, method: str, *args, **kwargs) -> RoutedResult:
        errors: list[str] = []
        for provider in self.providers:
            func = getattr(provider, method, None)
            if func is None:
                continue
            try:
                data = func(*args, **kwargs)
                return RoutedResult(
                    data=data,
                    source=provider.__class__.__name__,
                )
            except Exception as exc:  # provider/network degradation
                errors.append(
                    f"{provider.__class__.__name__}: {exc}"
                )
        joined = " | ".join(errors) if errors else "no compatible provider"
        raise RuntimeError(
            f"All providers failed for {method}: {joined}"
        )

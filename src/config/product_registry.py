"""
Product Registry — Loads and manages product configuration.

Products are defined in ``config/products.json`` and describe each fintech
app tracked by the pipeline (App Store IDs, Play Store IDs, Google Doc IDs,
stakeholder email lists, etc.).
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field


class ProductConfig(BaseModel):
    """Configuration for a single tracked product."""

    slug: str = Field(
        ...,
        description="URL-safe identifier (e.g., 'groww').",
    )
    display_name: str = Field(
        ...,
        description="Human-readable product name (e.g., 'Groww').",
    )
    appstore_id: str = Field(
        default="",
        description="Apple App Store numeric ID.",
    )
    playstore_id: str = Field(
        default="",
        description="Google Play Store package name (e.g., 'com.nextbillion.groww').",
    )
    doc_id: str = Field(
        default="",
        description="Google Docs document ID for the pulse report.",
    )
    doc_title: str = Field(
        default="",
        description="Title of the running Google Doc.",
    )
    stakeholder_emails: list[str] = Field(
        default_factory=list,
        description="Email addresses for stakeholder notifications.",
    )


class ProductRegistry:
    """
    Loads products from a JSON file and provides lookup by slug.

    Usage::

        registry = ProductRegistry.from_file("config/products.json")
        groww = registry.get("groww")
        all_products = registry.list_all()
    """

    def __init__(self, products: list[ProductConfig]) -> None:
        self._products = {p.slug: p for p in products}

    @classmethod
    def from_file(cls, path: str | Path) -> ProductRegistry:
        """Load the registry from a JSON file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Product registry not found: {path}")

        with open(path) as f:
            data = json.load(f)

        raw_products = data.get("products", [])
        products = [ProductConfig(**p) for p in raw_products]
        return cls(products)

    def get(self, slug: str) -> ProductConfig | None:
        """Look up a product by slug. Returns None if not found."""
        return self._products.get(slug)

    def get_or_raise(self, slug: str) -> ProductConfig:
        """Look up a product by slug. Raises KeyError if not found."""
        product = self._products.get(slug)
        if product is None:
            available = ", ".join(sorted(self._products.keys()))
            raise KeyError(
                f"Product '{slug}' not found in registry. Available: {available}"
            )
        return product

    def list_all(self) -> list[ProductConfig]:
        """Return all registered products."""
        return list(self._products.values())

    def list_slugs(self) -> list[str]:
        """Return all product slugs."""
        return sorted(self._products.keys())

    def __len__(self) -> int:
        return len(self._products)

    def __contains__(self, slug: str) -> bool:
        return slug in self._products

    def __repr__(self) -> str:
        slugs = ", ".join(self.list_slugs())
        return f"ProductRegistry([{slugs}])"

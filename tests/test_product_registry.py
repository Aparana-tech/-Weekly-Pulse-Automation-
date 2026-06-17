"""
Tests for ProductRegistry — loading, lookup, and validation.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.config.product_registry import ProductConfig, ProductRegistry


@pytest.fixture()
def sample_products_json(tmp_path: Path) -> Path:
    """Create a temporary products.json file."""
    data = {
        "products": [
            {
                "slug": "groww",
                "display_name": "Groww",
                "appstore_id": "1404871703",
                "playstore_id": "com.nextbillion.groww",
                "doc_id": "doc_abc123",
                "doc_title": "Weekly Review Pulse — Groww",
                "stakeholder_emails": ["product@example.com"],
            },
            {
                "slug": "kuvera",
                "display_name": "Kuvera",
                "appstore_id": "1341059498",
                "playstore_id": "com.goalgetter.kuvera",
                "doc_id": "doc_def456",
                "doc_title": "Weekly Review Pulse — Kuvera",
                "stakeholder_emails": ["team@example.com", "lead@example.com"],
            },
        ]
    }
    path = tmp_path / "products.json"
    path.write_text(json.dumps(data))
    return path


@pytest.fixture()
def registry(sample_products_json: Path) -> ProductRegistry:
    """Load a ProductRegistry from the sample file."""
    return ProductRegistry.from_file(sample_products_json)


class TestProductConfig:
    """Test ProductConfig model."""

    def test_create_product(self) -> None:
        p = ProductConfig(slug="groww", display_name="Groww")
        assert p.slug == "groww"
        assert p.display_name == "Groww"
        assert p.appstore_id == ""
        assert p.stakeholder_emails == []


class TestProductRegistryLoading:
    """Test registry file loading."""

    def test_load_from_file(self, sample_products_json: Path) -> None:
        reg = ProductRegistry.from_file(sample_products_json)
        assert len(reg) == 2

    def test_load_nonexistent_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            ProductRegistry.from_file(tmp_path / "nope.json")

    def test_load_from_project_config(self) -> None:
        """Load the real products.json from the project."""
        reg = ProductRegistry.from_file("config/products.json")
        assert len(reg) == 5
        assert "groww" in reg
        assert "kuvera" in reg


class TestProductRegistryLookup:
    """Test lookup operations on the registry."""

    def test_get_existing(self, registry: ProductRegistry) -> None:
        p = registry.get("groww")
        assert p is not None
        assert p.display_name == "Groww"
        assert p.appstore_id == "1404871703"

    def test_get_missing_returns_none(self, registry: ProductRegistry) -> None:
        assert registry.get("nonexistent") is None

    def test_get_or_raise_existing(self, registry: ProductRegistry) -> None:
        p = registry.get_or_raise("kuvera")
        assert p.display_name == "Kuvera"

    def test_get_or_raise_missing_raises(self, registry: ProductRegistry) -> None:
        with pytest.raises(KeyError, match="nonexistent"):
            registry.get_or_raise("nonexistent")


class TestProductRegistryList:
    """Test listing operations."""

    def test_list_all(self, registry: ProductRegistry) -> None:
        products = registry.list_all()
        assert len(products) == 2

    def test_list_slugs(self, registry: ProductRegistry) -> None:
        slugs = registry.list_slugs()
        assert slugs == ["groww", "kuvera"]

    def test_contains(self, registry: ProductRegistry) -> None:
        assert "groww" in registry
        assert "nonexistent" not in registry

    def test_len(self, registry: ProductRegistry) -> None:
        assert len(registry) == 2

    def test_repr(self, registry: ProductRegistry) -> None:
        r = repr(registry)
        assert "groww" in r
        assert "kuvera" in r

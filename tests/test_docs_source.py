# tests/test_docs_source.py
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sources.docs_source import DocsSource

FIXTURE_DIR = Path(__file__).parent / "data"
FIXTURE_FILE = FIXTURE_DIR / "docs_fixture.json"


def _rows(extract: str) -> list[dict]:
    source = DocsSource(str(FIXTURE_FILE), extract)
    return [row for batch in source.get_batches(10) for row in batch]


class TestDocsSourceFileResolution:
    def test_direct_file_path(self):
        source = DocsSource(str(FIXTURE_DIR / "docs_fixture.json"), "items")
        assert list(source.get_batches(10))

    def test_missing_file_raises(self, tmp_path):
        import pytest

        with pytest.raises(FileNotFoundError):
            DocsSource(str(tmp_path), "items")


class TestDocsSourceExtracts:
    def test_items(self):
        rows = _rows("items")
        by_class = {r["className"]: r for r in rows}
        assert set(by_class) == {"Desc_IronIngot_C", "Desc_IronPlate_C"}
        assert by_class["Desc_IronIngot_C"]["displayName"] == "Iron Ingot"
        assert by_class["Desc_IronIngot_C"]["form"] == "RF_SOLID"
        assert by_class["Desc_IronIngot_C"]["sinkPoints"] == 2

    def test_buildables(self):
        rows = _rows("buildables")
        assert len(rows) == 1
        assert rows[0]["className"] == "Build_ConstructorMk1_C"
        assert rows[0]["displayName"] == "Constructor"
        assert rows[0]["powerConsumption"] == 4.0

    def test_recipes_excludes_building_construction(self):
        rows = _rows("recipes")
        assert [r["className"] for r in rows] == ["Recipe_IronPlate_C"]
        assert rows[0]["durationSeconds"] == 6.0
        assert rows[0]["isAlternate"] is False

    def test_recipe_ingredients(self):
        rows = _rows("recipe_ingredients")
        assert rows == [
            {
                "recipeClassName": "Recipe_IronPlate_C",
                "itemClassName": "Desc_IronIngot_C",
                "amount": 3,
            }
        ]

    def test_recipe_products(self):
        rows = _rows("recipe_products")
        assert rows == [
            {
                "recipeClassName": "Recipe_IronPlate_C",
                "itemClassName": "Desc_IronPlate_C",
                "amount": 2,
            }
        ]

    def test_recipe_machines(self):
        rows = _rows("recipe_machines")
        assert rows == [
            {
                "recipeClassName": "Recipe_IronPlate_C",
                "buildableClassName": "Build_ConstructorMk1_C",
            }
        ]

    def test_schematics(self):
        rows = _rows("schematics")
        assert rows == [
            {
                "className": "Schematic_Test_C",
                "displayName": "Test Schematic",
                "tier": 0,
                "type": "EST_Custom",
            }
        ]

    def test_schematic_unlocks(self):
        rows = _rows("schematic_unlocks")
        assert rows == [
            {
                "schematicClassName": "Schematic_Test_C",
                "recipeClassName": "Recipe_IronPlate_C",
            }
        ]

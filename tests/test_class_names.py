# tests/test_class_names.py
"""
Real-data-derived cases for the two functions the entire logical/physical
join depends on. Pulled from an actual en-US.json + save inspection during
the docs-enrichment session — see .session/2026-08-12-docs-enrichment.md.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sources.class_names import (
    normalise_class,
    parse_item_amounts,
    parse_quoted_class_list,
)


class TestNormaliseClass:
    def test_save_instance_path(self):
        raw = "Persistent_Level:PersistentLevel.Build_ConstructorMk1_C_2147414321"
        assert normalise_class(raw) == "Build_ConstructorMk1_C"

    def test_bare_short_name(self):
        assert normalise_class("Build_ConstructorMk1_C") == "Build_ConstructorMk1_C"

    def test_save_recipe_reference(self):
        raw = "/Game/FactoryGame/Recipes/Constructor/Recipe_AlienDNACapsule.Recipe_AlienDNACapsule_C"
        assert normalise_class(raw) == "Recipe_AlienDNACapsule_C"

    def test_docs_produced_in_path(self):
        raw = "/Game/FactoryGame/Buildable/Factory/ConstructorMk1/Build_ConstructorMk1.Build_ConstructorMk1_C"
        assert normalise_class(raw) == "Build_ConstructorMk1_C"

    def test_docs_ingredient_quoted_engine_path(self):
        raw = (
            "/Script/Engine.BlueprintGeneratedClass"
            "'/Game/FactoryGame/Resource/Parts/IronIngot/Desc_IronIngot.Desc_IronIngot_C'"
        )
        assert normalise_class(raw) == "Desc_IronIngot_C"


class TestParseItemAmounts:
    def test_single_ingredient(self):
        raw = (
            "((ItemClass=\"/Script/Engine.BlueprintGeneratedClass"
            "'/Game/FactoryGame/Resource/Parts/IronIngot/Desc_IronIngot.Desc_IronIngot_C'\","
            "Amount=3))"
        )
        assert parse_item_amounts(raw) == [("Desc_IronIngot_C", 3)]

    def test_multi_ingredient(self):
        raw = (
            "((ItemClass=\"...IronRod.Desc_IronRod_C'\",Amount=10),"
            "(ItemClass=\"...IronPlateReinforced.Desc_IronPlateReinforced_C'\",Amount=2),"
            "(ItemClass=\"...Cable.Desc_Cable_C'\",Amount=15),"
            "(ItemClass=\"...Wire.Desc_Wire_C'\",Amount=50))"
        )
        assert parse_item_amounts(raw) == [
            ("Desc_IronRod_C", 10),
            ("Desc_IronPlateReinforced_C", 2),
            ("Desc_Cable_C", 15),
            ("Desc_Wire_C", 50),
        ]

    def test_empty_string(self):
        assert parse_item_amounts("") == []


class TestParseQuotedClassList:
    def test_produced_in(self):
        raw = (
            '("/Game/.../Build_ConstructorMk1.Build_ConstructorMk1_C",'
            '"/Game/.../BP_WorkBenchComponent.BP_WorkBenchComponent_C")'
        )
        assert parse_quoted_class_list(raw) == [
            "Build_ConstructorMk1_C",
            "BP_WorkBenchComponent_C",
        ]

    def test_empty_string(self):
        assert parse_quoted_class_list("") == []

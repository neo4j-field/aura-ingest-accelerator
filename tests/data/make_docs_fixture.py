# tests/data/make_docs_fixture.py
"""
Regenerates docs_fixture.json (UTF-16, matching the real en-US.json encoding).
Run manually if the fixture needs to change:
    uv run python tests/data/make_docs_fixture.py
Never replace this with a copy of the real game file — see AGENTS.md
Project-Specific "Locked decisions" (never vendor Coffee Stain's content).
"""
import json
from pathlib import Path

DATA = [
    {
        "NativeClass": "/Script/CoreUObject.Class'/Script/FactoryGame.FGItemDescriptor'",
        "Classes": [
            {
                "ClassName": "Desc_IronIngot_C",
                "mDisplayName": "Iron Ingot",
                "mDescription": "Used for crafting the most basic parts.",
                "mForm": "RF_SOLID",
                "mStackSize": "SS_MEDIUM",
                "mEnergyValue": "0.000000",
                "mResourceSinkPoints": "2",
            },
            {
                "ClassName": "Desc_IronPlate_C",
                "mDisplayName": "Iron Plate",
                "mDescription": "A sheet of iron.",
                "mForm": "RF_SOLID",
                "mStackSize": "SS_MEDIUM",
                "mEnergyValue": "0.000000",
                "mResourceSinkPoints": "3",
            },
        ],
    },
    {
        "NativeClass": "/Script/CoreUObject.Class'/Script/FactoryGame.FGBuildableManufacturer'",
        "Classes": [
            {
                "ClassName": "Build_ConstructorMk1_C",
                "mDisplayName": "Constructor",
                "mDescription": "Crafts 1 part into another part.",
                "mPowerConsumption": "4.000000",
                "mPowerConsumptionExponent": "1.321929",
                "mManufacturingSpeed": "1.000000",
            }
        ],
    },
    {
        "NativeClass": "/Script/CoreUObject.Class'/Script/FactoryGame.FGRecipe'",
        "Classes": [
            {
                "ClassName": "Recipe_IronPlate_C",
                "mDisplayName": "Iron Plate",
                "mIngredients": (
                    "((ItemClass=\"/Script/Engine.BlueprintGeneratedClass"
                    "'/Game/FactoryGame/Resource/Parts/IronIngot/Desc_IronIngot"
                    ".Desc_IronIngot_C'\",Amount=3))"
                ),
                "mProduct": (
                    "((ItemClass=\"/Script/Engine.BlueprintGeneratedClass"
                    "'/Game/FactoryGame/Resource/Parts/IronPlate/Desc_IronPlate"
                    ".Desc_IronPlate_C'\",Amount=2))"
                ),
                "mManufactoringDuration": "6.000000",
                "mProducedIn": (
                    '("/Game/FactoryGame/Buildable/Factory/ConstructorMk1/'
                    'Build_ConstructorMk1.Build_ConstructorMk1_C")'
                ),
            },
            {
                # Building-construction recipe — must be excluded from the
                # "recipes" / "recipe_ingredients" / "recipe_machines" extracts.
                "ClassName": "Recipe_BuildConstructorMk1_C",
                "mDisplayName": "N/A",
                "mIngredients": "",
                "mProduct": "",
                "mManufactoringDuration": "1.000000",
                "mProducedIn": (
                    '("/Game/FactoryGame/Equipment/BuildGun/BP_BuildGun.BP_BuildGun_C")'
                ),
            },
        ],
    },
    {
        "NativeClass": "/Script/CoreUObject.Class'/Script/FactoryGame.FGSchematic'",
        "Classes": [
            {
                "ClassName": "Schematic_Test_C",
                "mDisplayName": "Test Schematic",
                "mTechTier": "0",
                "mType": "EST_Custom",
                "mUnlocks": [
                    {
                        "Class": "BP_UnlockRecipe_C",
                        "mRecipes": (
                            '("/Game/FactoryGame/Recipes/Constructor/'
                            'Recipe_IronPlate.Recipe_IronPlate_C")'
                        ),
                    }
                ],
            }
        ],
    },
]

out = Path(__file__).parent / "docs_fixture.json"
out.write_text(json.dumps(DATA, indent=2), encoding="utf-16")
print(f"wrote {out}")

# sources/docs_source.py
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from sources.base import BaseSource
from sources.class_names import (
    normalise_class,
    parse_item_amounts,
    parse_quoted_class_list,
)

logger = logging.getLogger(__name__)

_PARSE_CACHE: dict[tuple[str, int, int], dict] = {}

_DOCS_FILENAMES = ("en-US.json", "Docs.json")

# NativeClass groups that hold item-like descriptors. category is a coarse
# source tag carried through to the postimport pass, which combines it with
# mForm to assign the final :Item secondary label (RawResource/Ingot/Part/
# Fluid/Ammo/Equipment/Consumable) — see AGENTS.md Project-Specific.
_ITEM_NATIVE_CLASSES = {
    "FGResourceDescriptor": "resource",
    "FGItemDescriptor": "item",
    "FGItemDescriptorBiomass": "biomass",
    "FGConsumableDescriptor": "consumable",
    "FGEquipmentDescriptor": "equipment",
    "FGAmmoTypeProjectile": "ammo",
    "FGAmmoTypeSpreadshot": "ammo",
    "FGAmmoTypeInstantHit": "ammo",
    "FGItemDescriptorNuclearFuel": "nuclearFuel",
    "FGPowerShardDescriptor": "powerShard",
    "FGItemDescriptorPowerBoosterFuel": "boosterFuel",
}

_FLUID_FORMS = {"RF_LIQUID", "RF_GAS"}

# Recipes produced only in the build gun are building-construction recipes,
# not production recipes — see the docs-enrichment session's real-file
# analysis (549 of 872 FGRecipe entries are BP_BuildGun_C-only).
_NON_PRODUCTION_TARGETS = {"BP_BuildGun_C", "FGBuildGun"}


def _to_float(v) -> float | None:
    if v in (None, ""):
        return None
    return float(v)


class DocsSource(BaseSource):
    """
    Reads a Satisfactory CommunityResources game-data dump (en-US.json, or
    the legacy Docs.json filename) and yields one of several named row
    projections — the logical (class/recipe) layer that joins to the
    physical (instance) layer from SatisfactorySource.

    No third-party parser required — the file is plain UTF-16 JSON with a
    handful of UE-struct-encoded string fields (mIngredients, mProduct,
    mProducedIn, mRecipes) parsed by sources.class_names.

    Args:
        docs_path: Either the Docs directory (containing en-US.json /
                   Docs.json) or a direct path to the file itself.
        extract:   Which projection to yield. One of EXTRACTS.
    """

    EXTRACTS = (
        "items",
        "buildables",
        "recipes",
        "recipe_ingredients",
        "recipe_products",
        "recipe_machines",
        "schematics",
        "schematic_unlocks",
    )

    def __init__(self, docs_path: str, extract: str):
        if extract not in self.EXTRACTS:
            raise ValueError(
                f"Unknown extract '{extract}'. "
                f"Valid options: {', '.join(self.EXTRACTS)}"
            )
        # config-docs.yaml jobs reference the path as "${SATISFACTORY_DOCS_PATH}" —
        # expand it here since this repo's config loader does no env-var
        # interpolation of its own (same convention as SatisfactorySource).
        load_dotenv()
        raw = Path(os.path.expandvars(docs_path)).expanduser().resolve()
        self.docs_path = self._resolve_file(raw)
        self.extract = extract

    @staticmethod
    def _resolve_file(raw: Path) -> Path:
        if raw.is_file():
            return raw
        for name in _DOCS_FILENAMES:
            candidate = raw / name
            if candidate.is_file():
                return candidate
        raise FileNotFoundError(
            f"No {' or '.join(_DOCS_FILENAMES)} found at {raw}"
        )

    def get_batches(self, batch_size: int):
        rows = getattr(self, f"_extract_{self.extract}")(self._docs())
        batch = []
        for row in rows:
            batch.append(row)
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch

    def _docs(self) -> dict:
        st = self.docs_path.stat()
        key = (str(self.docs_path), st.st_mtime_ns, st.st_size)
        if key not in _PARSE_CACHE:
            logger.info("Parsing docs file %s …", self.docs_path.name)
            _PARSE_CACHE.clear()  # only ever cache one docs file at a time
            with open(self.docs_path, encoding="utf-16") as f:
                data = json.load(f)
            _PARSE_CACHE[key] = {g["NativeClass"]: g["Classes"] for g in data}
            logger.info("Parse complete — %d native-class groups.", len(data))
        return _PARSE_CACHE[key]

    @staticmethod
    def _group(by_native: dict, native_class_name: str) -> list:
        """Exact-match a single NativeClass group by its bare name (e.g. 'FGRecipe')."""
        for full, classes in by_native.items():
            if full.endswith(f"{native_class_name}'"):
                return classes
        return []

    def _item_forms(self, by_native: dict) -> dict[str, str]:
        """className -> mForm, across every item-like native class. Used to
        detect fluid recipes (amounts stored in mL — see _extract_recipe_*)."""
        forms = {}
        for full, classes in by_native.items():
            if not any(full.endswith(f"{k}'") for k in _ITEM_NATIVE_CLASSES):
                continue
            for c in classes:
                forms[c["ClassName"]] = c.get("mForm", "RF_INVALID")
        return forms

    def _production_recipes(self, by_native: dict):
        """FGRecipe entries with a real production building, filtering out
        the ~550 build-gun-only building-construction recipes."""
        for r in self._group(by_native, "FGRecipe"):
            targets = parse_quoted_class_list(r.get("mProducedIn", ""))
            if not targets or set(targets) <= _NON_PRODUCTION_TARGETS:
                continue
            yield r, targets

    # -------------------------------------------------------------------
    # Extracts
    # -------------------------------------------------------------------

    def _extract_items(self, by_native):
        for full, classes in by_native.items():
            category = next(
                (v for k, v in _ITEM_NATIVE_CLASSES.items() if full.endswith(f"{k}'")),
                None,
            )
            if category is None:
                continue
            for c in classes:
                yield {
                    "className": c["ClassName"],
                    "displayName": c.get("mDisplayName", ""),
                    "description": c.get("mDescription", ""),
                    "form": c.get("mForm", "RF_INVALID"),
                    "category": category,
                    "stackSize": c.get("mStackSize", ""),
                    "sinkPoints": int(c.get("mResourceSinkPoints") or 0),
                    "energyValue": _to_float(c.get("mEnergyValue")) or 0.0,
                }

    def _extract_buildables(self, by_native):
        seen: set[str] = set()
        for full, classes in by_native.items():
            if "FGBuildable" not in full:
                continue
            for c in classes:
                class_name = c["ClassName"]
                if class_name in seen:
                    continue
                seen.add(class_name)
                yield {
                    "className": class_name,
                    "displayName": c.get("mDisplayName", ""),
                    "description": c.get("mDescription", ""),
                    "powerConsumption": _to_float(c.get("mPowerConsumption")),
                    "powerConsumptionExponent": _to_float(
                        c.get("mPowerConsumptionExponent")
                    ),
                    "manufacturingSpeed": _to_float(c.get("mManufacturingSpeed")),
                }

    def _extract_recipes(self, by_native):
        for r, _targets in self._production_recipes(by_native):
            yield {
                "className": r["ClassName"],
                "displayName": r.get("mDisplayName", ""),
                "durationSeconds": _to_float(r.get("mManufactoringDuration")) or 0.0,
                "isAlternate": r.get("mDisplayName", "").startswith("Alternate:"),
            }

    def _extract_recipe_ingredients(self, by_native):
        forms = self._item_forms(by_native)
        for r, _targets in self._production_recipes(by_native):
            for item_class, amount in parse_item_amounts(r.get("mIngredients", "")):
                if forms.get(item_class) in _FLUID_FORMS:
                    amount = amount / 1000  # mL -> m^3, see Gotcha #1
                yield {
                    "recipeClassName": r["ClassName"],
                    "itemClassName": item_class,
                    "amount": amount,
                }

    def _extract_recipe_products(self, by_native):
        forms = self._item_forms(by_native)
        for r, _targets in self._production_recipes(by_native):
            for item_class, amount in parse_item_amounts(r.get("mProduct", "")):
                if forms.get(item_class) in _FLUID_FORMS:
                    amount = amount / 1000
                yield {
                    "recipeClassName": r["ClassName"],
                    "itemClassName": item_class,
                    "amount": amount,
                }

    def _extract_recipe_machines(self, by_native):
        for r, targets in self._production_recipes(by_native):
            for buildable_class in targets:
                yield {
                    "recipeClassName": r["ClassName"],
                    "buildableClassName": buildable_class,
                }

    def _extract_schematics(self, by_native):
        for s in self._group(by_native, "FGSchematic"):
            yield {
                "className": s["ClassName"],
                "displayName": s.get("mDisplayName", ""),
                "tier": int(s.get("mTechTier") or 0),
                "type": s.get("mType", ""),
            }

    def _extract_schematic_unlocks(self, by_native):
        for s in self._group(by_native, "FGSchematic"):
            for unlock in s.get("mUnlocks") or []:
                if unlock.get("Class") != "BP_UnlockRecipe_C":
                    continue
                for recipe_class in parse_quoted_class_list(unlock.get("mRecipes", "")):
                    yield {
                        "schematicClassName": s["ClassName"],
                        "recipeClassName": recipe_class,
                    }

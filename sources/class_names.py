# sources/class_names.py
"""
Shared class-name normalisation for the Satisfactory connectors.

The save file (SatisfactorySource) and the Docs.json game-data dump
(DocsSource) reference the same game classes in different string shapes —
full UE package paths, level-qualified instance paths, or bare short names.
Both sides must reduce to the same key or every join edge between the
physical (save) and logical (docs) layers silently produces zero rows.
"""
import re

_INSTANCE_SUFFIX_RE = re.compile(r"_\d+$")
_QUOTED_PATH_RE = re.compile(r'"([^"]+)"')

# Handles the real mIngredients / mProduct format:
#   ((ItemClass="/Script/Engine.BlueprintGeneratedClass'/Game/.../Desc_IronIngot.Desc_IronIngot_C'",Amount=3))
# Trailing quote characters after the class name can be a UE single-quote
# followed by a JSON double-quote back to back — `['"]?` (zero-or-one) misses
# the second one, which is why a *-quantified class works and a ?-quantified
# one silently matches nothing. Verified against all 872 real FGRecipe
# entries (1738 ingredient/product fields) in en-US.json before trusting it.
_ITEM_AMOUNT_RE = re.compile(r"ItemClass=.*?([A-Za-z0-9_]+_C)['\"]*\s*,\s*Amount=(\d+)")


def normalise_class(raw: str) -> str:
    """Reduce any class reference (save path, docs path, bare name) to its short class name."""
    s = raw.strip().strip("'\"")
    s = s.rsplit(".", 1)[-1]  # drop package path
    s = s.rsplit(":", 1)[-1]  # drop level prefix
    s = _INSTANCE_SUFFIX_RE.sub("", s)  # drop instance suffix (…_C_2147414321 -> …_C)
    return s


def parse_item_amounts(raw: str) -> list[tuple[str, int]]:
    """Parse an mIngredients / mProduct string into [(className, amount), ...]."""
    if not raw:
        return []
    return [(m.group(1), int(m.group(2))) for m in _ITEM_AMOUNT_RE.finditer(raw)]


def parse_quoted_class_list(raw: str) -> list[str]:
    """
    Parse a UE quoted-path-list string (mProducedIn, mRecipes, ...) into
    normalised short class names:
      ("/Game/.../Build_ConstructorMk1.Build_ConstructorMk1_C","...")
    """
    if not raw:
        return []
    return [normalise_class(m.group(1)) for m in _QUOTED_PATH_RE.finditer(raw)]

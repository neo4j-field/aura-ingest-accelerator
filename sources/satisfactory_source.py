# sources/satisfactory_source.py
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from sources.base import BaseSource
from sources.class_names import normalise_class

logger = logging.getLogger(__name__)

_PARSE_CACHE: dict[tuple[str, int, int], object] = {}

_FACTORY_CONNECTION_CLASS = "FGFactoryConnectionComponent"
_PIPE_CONNECTION_CLASS = "FGPipeConnectionComponent"
_POWER_CIRCUIT_CLASS = "/Script/FactoryGame.FGPowerCircuit"
_INVENTORY_CLASS = "FGInventoryComponent"


def _owner_of(path: str) -> str:
    """An object's owning actor is everything before its last path segment."""
    return path.rsplit(".", 1)[0]


def _short_name(type_path: str) -> str:
    return type_path.rsplit(".", 1)[-1]


def _category_for(short_name: str, type_path: str, machine_typepaths: set[str]) -> str:
    if short_name.startswith(("Build_ConveyorBelt", "Build_ConveyorLift")):
        return "conveyor"
    if short_name.startswith("Build_Pipeline"):
        return "pipe"
    if short_name.startswith(("Build_PowerLine", "Build_PowerPole")):
        return "power"
    if short_name.startswith("Build_"):
        return "machine" if type_path in machine_typepaths else "building"
    if short_name.startswith("BP_Player"):
        return "player"
    return "other"


class SatisfactorySource(BaseSource):
    """
    Reads a Satisfactory .sav file and yields one of several named row projections.

    Requires the optional parser dependency:
        pip install aura-ingest-accelerator[satisfactory]

    Args:
        save_path: Path to the .sav file. Read-only; never written.
        extract:   Which projection to yield. One of EXTRACTS.

    Note: unlike the other sources in this repo, this one parses the entire input
    into memory before yielding — a save's cross-references (belt endpoints, power
    circuits) can't be resolved without the full object graph. See Known Issues in
    AGENTS.md.
    """

    EXTRACTS = (
        "save",
        "levels",
        "classes",
        "actors",
        "inventory_stacks",
        "factory_links",
        "power_links",
        "machine_recipes",
    )

    def __init__(self, save_path: str, extract: str):
        if extract not in self.EXTRACTS:
            raise ValueError(
                f"Unknown extract '{extract}'. "
                f"Valid options: {', '.join(self.EXTRACTS)}"
            )
        # config.yaml jobs reference the path as "${SATISFACTORY_SAVE_PATH}" so
        # every extract shares one .env-configured save; expand it here since
        # this repo's config loader does no env-var interpolation of its own.
        load_dotenv()
        self.save_path = Path(os.path.expandvars(save_path)).expanduser().resolve()
        if not self.save_path.is_file():
            raise FileNotFoundError(f"Save file not found: {self.save_path}")
        self.extract = extract

    def get_batches(self, batch_size: int):
        rows = getattr(self, f"_extract_{self.extract}")(self._save())
        batch = []
        for row in rows:
            batch.append(row)
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch

    def _save(self):
        st = self.save_path.stat()
        key = (str(self.save_path), st.st_mtime_ns, st.st_size)
        if key not in _PARSE_CACHE:
            import satisfactory_save  # lazy — optional dependency

            logger.info("Parsing save file %s …", self.save_path.name)
            _PARSE_CACHE.clear()  # only ever cache one save at a time
            _PARSE_CACHE[key] = satisfactory_save.SaveGame(str(self.save_path))
            logger.info("Parse complete.")
        return _PARSE_CACHE[key]

    def _machine_typepaths(self, save) -> set[str]:
        """
        Type paths that own >=1 FGFactoryConnectionComponent in at least one
        instance — used to split the generic 'building' category into 'machine'.
        """
        objs = save.allSaveObjects()
        class_by_path = {
            o.BaseHeader.Reference.PathName: o.BaseHeader.ClassName for o in objs
        }
        machine_typepaths: set[str] = set()
        for o in objs:
            if _FACTORY_CONNECTION_CLASS not in o.BaseHeader.ClassName:
                continue
            owner_class = class_by_path.get(_owner_of(o.BaseHeader.Reference.PathName))
            if owner_class:
                machine_typepaths.add(owner_class)
        return machine_typepaths

    # -------------------------------------------------------------------
    # Extracts
    # -------------------------------------------------------------------

    def _extract_save(self, save):
        sh = save.mSaveHeader
        saved_at = datetime.strptime(
            sh.SaveDateTime.toString(), "%Y-%m-%d %H:%M:%S"
        ).replace(tzinfo=timezone.utc)
        yield {
            "saveId": sh.SaveIdentifier,
            "sessionName": sh.SessionName,
            "playDurationSeconds": int(sh.PlayDurationSeconds),
            "saveVersion": int(sh.SaveVersion),
            "buildVersion": int(sh.BuildVersion),
            "savedAtEpochMillis": int(saved_at.timestamp() * 1000),
        }

    def _extract_levels(self, save):
        save_id = save.mSaveHeader.SaveIdentifier
        yield {
            "saveId": save_id,
            "levelName": save.mSaveHeader.MapName,
            "isPersistent": True,
        }
        for key in save.mPerLevelDataMap.Keys:
            yield {"saveId": save_id, "levelName": key, "isPersistent": False}

    def _extract_classes(self, save):
        machine_typepaths = self._machine_typepaths(save)
        seen: set[str] = set()
        for o in save.allSaveObjects():
            type_path = o.BaseHeader.ClassName
            if type_path in seen:
                continue
            seen.add(type_path)
            short_name = _short_name(type_path)
            yield {
                "typePath": type_path,
                "shortName": short_name,
                "category": _category_for(short_name, type_path, machine_typepaths),
            }

    def _extract_actors(self, save):
        machine_typepaths = self._machine_typepaths(save)
        for o in save.allSaveObjects():
            if not o.isActor():
                continue
            ref = o.BaseHeader.Reference
            type_path = o.BaseHeader.ClassName
            short_name = _short_name(type_path)
            category = _category_for(short_name, type_path, machine_typepaths)

            header = o.Header
            transform = getattr(header, "Transform", None) if header is not None else None
            if transform is not None:
                pos, rot, scale = transform.Translation, transform.Rotation, transform.Scale3D
                row_transform = {
                    "posX": float(pos.X), "posY": float(pos.Y), "posZ": float(pos.Z),
                    "rotX": float(rot.X), "rotY": float(rot.Y),
                    "rotZ": float(rot.Z), "rotW": float(rot.W),
                    "scaleX": float(scale.X), "scaleY": float(scale.Y), "scaleZ": float(scale.Z),
                }
            else:
                logger.debug("No transform for actor %s — emitting nulls", ref.PathName)
                row_transform = {
                    "posX": None, "posY": None, "posZ": None,
                    "rotX": None, "rotY": None, "rotZ": None, "rotW": None,
                    "scaleX": None, "scaleY": None, "scaleZ": None,
                }

            yield {
                "instanceName": ref.PathName,
                "typePath": type_path,
                "levelName": ref.LevelName,
                "category": category,
                **row_transform,
            }

    def _extract_inventory_stacks(self, save):
        for o in save.allSaveObjects():
            if _INVENTORY_CLASS not in o.BaseHeader.ClassName:
                continue
            if o.Object is None:
                logger.debug(
                    "Skipping unparsed inventory component %s",
                    o.BaseHeader.Reference.PathName,
                )
                continue
            owner = _owner_of(o.BaseHeader.Reference.PathName)
            for p in o.Object.Properties:
                if p.Name.toString() != "mInventoryStacks":
                    continue
                for slot_index, stack in enumerate(p.Value.Values):
                    item_class = None
                    num_items = 0
                    for dp in stack.Data:
                        dp_name = dp.Name.toString()
                        if dp_name == "NumItems":
                            num_items = int(dp.Value)
                        elif dp_name == "Item":
                            item_class = getattr(
                                getattr(dp.Value, "Data", None), "ItemClass", None
                            )
                            item_class = getattr(item_class, "PathName", None)
                    if num_items <= 0 or item_class is None:
                        continue
                    yield {
                        "ownerInstanceName": owner,
                        # normalised to match Item.className from DocsSource —
                        # see docs-enrichment session, class_names.normalise_class
                        "itemClass": normalise_class(item_class),
                        "slotIndex": slot_index,
                        "count": num_items,
                    }

    def _extract_factory_links(self, save):
        """
        FGFactoryConnectionComponent / FGPipeConnectionComponent have no
        mDirection property — direction is encoded in the component's own name:
        'Output*' / 'Input*' on buildings, or an index-parity convention
        (0 = inbound, 1 = outbound) on ambiguous belt/pipe endpoints
        ('ConveyorAny*', 'PipelineConnection*', 'SnapOnly*', 'Connection*').
        This is a heuristic pending ground-truth validation — see AGENTS.md
        Known Issues.
        """
        objs = save.allSaveObjects()
        comps: dict[str, tuple[bool, str, str]] = {}
        for o in objs:
            cls = o.BaseHeader.ClassName
            if _FACTORY_CONNECTION_CLASS in cls:
                kind = "conveyor"
            elif _PIPE_CONNECTION_CLASS in cls:
                kind = "pipe"
            else:
                continue
            if o.Object is None:
                continue
            path = o.BaseHeader.Reference.PathName
            connected = None
            for p in o.Object.Properties:
                if p.Name.toString() == "mConnectedComponent":
                    connected = p.Value.PathName
                    break
            if connected is None:
                logger.debug("Dangling factory connection (no partner): %s", path)
                continue

            name = path.rsplit(".", 1)[-1]
            prefix = re.sub(r"\d+$", "", name)
            digit_match = re.search(r"(\d+)$", name)
            index = int(digit_match.group(1)) if digit_match else 0
            is_output = prefix == "Output" or (prefix != "Input" and index >= 1)
            comps[path] = (is_output, connected, kind)

        for path, (is_output, connected, kind) in comps.items():
            if not is_output:
                continue
            owner_from, owner_to = _owner_of(path), _owner_of(connected)
            if owner_from == owner_to:
                continue
            yield {
                "fromInstanceName": owner_from,
                "toInstanceName": owner_to,
                "kind": kind,
            }

    def _extract_power_links(self, save):
        for o in save.allSaveObjects():
            if o.BaseHeader.ClassName != _POWER_CIRCUIT_CLASS:
                continue
            if o.Object is None:
                continue
            circuit_id = None
            components = []
            for p in o.Object.Properties:
                name = p.Name.toString()
                if name == "mCircuitID":
                    circuit_id = int(p.Value)
                elif name == "mComponents":
                    components = p.Value.Values
            if circuit_id is None:
                logger.debug(
                    "Skipping power circuit with no mCircuitID: %s",
                    o.BaseHeader.Reference.PathName,
                )
                continue
            for comp_ref in components:
                comp_path = getattr(comp_ref, "PathName", None)
                if comp_path is None:
                    continue
                yield {"instanceName": _owner_of(comp_path), "circuitId": circuit_id}

    def _extract_machine_recipes(self, save):
        """
        The RUNS_RECIPE join edge to the DocsSource logical layer — see
        .session/2026-08-12-docs-enrichment.md. Only manufacturer-style
        buildings (Constructor, Assembler, Manufacturer, Refinery, Blender,
        Foundry, Packager, ...) carry mCurrentRecipe; miners/extractors don't
        (they auto-extract with no recipe) and are silently skipped.
        """
        for o in save.allSaveObjects():
            if o.Object is None:
                continue
            recipe_path = None
            clock_speed = None
            for p in o.Object.Properties:
                name = p.Name.toString()
                if name == "mCurrentRecipe":
                    recipe_path = getattr(p.Value, "PathName", None)
                elif name == "mCurrentPotential":
                    clock_speed = float(p.Value)
            if recipe_path is None:
                continue
            yield {
                "instanceName": o.BaseHeader.Reference.PathName,
                "recipeClassName": normalise_class(recipe_path),
                "clockSpeed": clock_speed,
            }

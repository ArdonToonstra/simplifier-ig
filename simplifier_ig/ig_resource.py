"""Generates an ImplementationGuide.json FHIR resource (R4 format)."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .utils import format_title
from .yaml_helpers import load_yaml


class IGResourceGenerator:
    """Generates an ImplementationGuide.json FHIR resource (R4 format)."""

    def __init__(self, guide_output_dir: str, input_dir: Optional[str] = None, log=None):
        self._guide_output_dir = Path(guide_output_dir).resolve()
        self._input_dir = Path(input_dir).resolve() if input_dir else None
        self._log = log or (lambda msg: None)
        self._config: Optional[Dict[str, str]] = None
        self._resources: List[Dict[str, Any]] = []

    # -- static validation --

    @staticmethod
    def validate_guide_yaml_for_ig_resource(input_dir: str) -> Tuple[bool, List[str]]:
        """Check that guide.yaml has all required fields for IG resource generation."""
        errors: List[str] = []
        guide_path = Path(input_dir) / "guide.yaml"

        if not guide_path.is_file():
            errors.append("guide.yaml not found")
            return False, errors

        try:
            config = load_yaml(guide_path)
            if not config:
                errors.append("guide.yaml is empty or invalid")
                return False, errors

            for field in ("id", "status", "fhirVersion", "canonical"):
                val = config.get(field)
                if not val or not str(val).strip():
                    errors.append(f"guide.yaml is missing required field for IG resource generation: '{field}'")

            status_val = config.get("status")
            if status_val:
                sv = str(status_val).strip().lower()
                if sv not in {"draft", "active", "retired", "unknown"}:
                    errors.append(f"Invalid status value '{sv}'. Must be one of: draft, active, retired, unknown")
        except Exception as e:
            errors.append(f"Error parsing guide.yaml: {e}")

        return len(errors) == 0, errors

    # -- public --

    def generate(self) -> Dict[str, Any]:
        result = {"success": False, "output_path": "", "page_count": 0, "errors": [], "warnings": []}

        try:
            self._log("[IG-RESOURCE] Starting ImplementationGuide resource generation...")

            # Step 1: Load config
            self._load_config(result)
            if result["errors"]:
                return result

            # Step 2: Build page structure
            home_dir = self._guide_output_dir / "Home"
            if not home_dir.is_dir():
                result["errors"].append(f"Home directory not found: {home_dir}")
                return result

            root_page = self._build_page_structure(home_dir, "Home")
            result["page_count"] = self._count_pages(root_page)
            self._log(f"[IG-RESOURCE] Built page structure with {result['page_count']} pages")

            # Step 3: Collect resources from input
            if self._input_dir:
                self._collect_resources()
                self._log(f"[IG-RESOURCE] Collected {len(self._resources)} resources for definition.resource")

            # Step 4: Build the IG resource as a dict (R4 format)
            ig = self._create_ig_resource_r4(root_page)

            # Step 5: Write JSON
            output_path = self._guide_output_dir / "ImplementationGuide.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(ig, f, indent=2, ensure_ascii=False)

            result["output_path"] = str(output_path)
            result["success"] = True
            self._log(f"[IG-RESOURCE] Generated ImplementationGuide.json at: {output_path}")

        except Exception as e:
            result["errors"].append(f"Error generating ImplementationGuide resource: {e}")

        return result

    # -- private --

    def _load_config(self, result):
        guide_yaml_path = self._guide_output_dir / "guide.yaml"
        if not guide_yaml_path.is_file():
            result["errors"].append("guide.yaml not found in output directory")
            return

        try:
            config = load_yaml(guide_yaml_path)
            if not config:
                result["errors"].append("guide.yaml is empty or invalid")
                return

            self._config = {}

            for field in ("id", "status", "fhirVersion", "canonical"):
                val = config.get(field)
                if val and str(val).strip():
                    self._config[field] = str(val).strip()
                else:
                    result["errors"].append(f"Missing required field '{field}' in guide.yaml")

            # status lowercase
            if "status" in self._config:
                self._config["status"] = self._config["status"].lower()

            # optional
            for opt in ("version", "title"):
                val = config.get(opt)
                if val and str(val).strip():
                    self._config[opt] = str(val).strip()

            if result["errors"]:
                result["errors"].insert(0, "IG resource generation requires additional fields in guide.yaml:")
        except Exception as e:
            result["errors"].append(f"Error reading guide.yaml: {e}")

    def _build_page_structure(self, directory: Path, relative_path: str) -> Dict:
        """Build a tree of PageNode dicts."""
        dir_name = directory.name
        page = {
            "nameUrl": relative_path,
            "title": format_title(dir_name),
            "generation": "generated",
            "children": [],
        }

        # .page.md files
        files = sorted(
            [f for f in directory.iterdir() if f.is_file() and f.name.endswith(".page.md")],
            key=lambda f: (0 if f.name.lower() == "index.page.md" else 1, f.name),
        )
        for f in files:
            title = format_title(f.name.replace(".page.md", ""))
            page["children"].append({
                "nameUrl": f"{relative_path}/{f.name}",
                "title": title,
                "generation": "markdown",
                "children": [],
            })

        # subdirectories
        subdirs = sorted(
            [
                d
                for d in directory.iterdir()
                if d.is_dir() and not d.name.startswith("_") and not d.name.startswith(".") and d.name != "pagetemplates"
            ],
            key=lambda d: d.name,
        )
        for sd in subdirs:
            child = self._build_page_structure(sd, f"{relative_path}/{sd.name}")
            page["children"].append(child)

        return page

    @staticmethod
    def _count_pages(page: Dict) -> int:
        count = 1
        for child in page.get("children", []):
            count += IGResourceGenerator._count_pages(child)
        return count

    def _collect_resources(self):
        self._resources.clear()
        if not self._input_dir:
            return

        # Conformance resources
        res_dir = self._input_dir / "resources"
        if res_dir.is_dir():
            for f in sorted(res_dir.glob("*.json")):
                entry = self._parse_resource_file(f, is_example=False)
                if entry:
                    self._resources.append(entry)

        # Examples
        ex_dir = self._input_dir / "examples"
        if ex_dir.is_dir():
            for f in sorted(ex_dir.glob("*.json")):
                entry = self._parse_resource_file(f, is_example=True)
                if entry:
                    self._resources.append(entry)

    @staticmethod
    def _extract_human_name(value: Any) -> Optional[str]:
        """Extract a readable name from a FHIR HumanName or list of HumanName."""
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            # List of HumanName – pick the first entry
            for hn in value:
                if isinstance(hn, dict):
                    if hn.get("text"):
                        return str(hn["text"])
                    parts: List[str] = []
                    given = hn.get("given")
                    if isinstance(given, list):
                        parts.extend(str(g) for g in given)
                    family = hn.get("family")
                    if family:
                        parts.append(str(family))
                    if parts:
                        return " ".join(parts)
                elif isinstance(hn, str):
                    return hn
        if isinstance(value, dict):
            if value.get("text"):
                return str(value["text"])
        return None

    @staticmethod
    def _extract_codeable_text(value: Any) -> Optional[str]:
        """Extract readable text from a FHIR CodeableConcept, Coding, or plain string."""
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            # CodeableConcept: prefer .text, then first coding.display
            if value.get("text"):
                return str(value["text"])
            codings = value.get("coding")
            if isinstance(codings, list):
                for coding in codings:
                    if isinstance(coding, dict) and coding.get("display"):
                        return str(coding["display"])
        if isinstance(value, list):
            # Unexpected list – try first element
            for item in value:
                result = IGResourceGenerator._extract_codeable_text(item)
                if result:
                    return result
        return None

    def _parse_resource_file(self, file_path: Path, is_example: bool) -> Optional[Dict[str, Any]]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                resource = json.load(f)

            rt = resource.get("resourceType")
            rid = resource.get("id")
            if not rt or not rid:
                self._log(f"[IG-RESOURCE] Warning: Skipping {file_path.name} - missing resourceType or id")
                return None

            entry: Dict[str, Any] = {
                "resourceType": rt,
                "id": rid,
                "isExample": is_example,
                "name": None,
                "description": None,
                "exampleCanonical": None,
                "url": None,
            }

            # name: may be a plain string or a complex type like HumanName[]
            raw_name = resource.get("name")
            if isinstance(raw_name, str):
                entry["name"] = raw_name
            elif raw_name is not None:
                entry["name"] = self._extract_human_name(raw_name) or format_title(rid)
            else:
                entry["name"] = format_title(rid)

            # description: may be a plain string or a CodeableConcept
            raw_desc = resource.get("description")
            if isinstance(raw_desc, str):
                entry["description"] = raw_desc
            elif raw_desc is not None:
                entry["description"] = self._extract_codeable_text(raw_desc)

            if is_example:
                meta = resource.get("meta", {})
                profiles = meta.get("profile", [])
                if profiles:
                    entry["exampleCanonical"] = str(profiles[0])
            else:
                url = resource.get("url")
                if url:
                    entry["url"] = str(url)

            return entry
        except Exception as e:
            self._log(f"[IG-RESOURCE] Warning: Error parsing {file_path.name}: {e}")
            return None

    def _create_ig_resource_r4(self, root_page: Dict) -> Dict[str, Any]:
        """Build an R4 ImplementationGuide resource as a plain dict."""
        cfg = self._config
        canonical = cfg["canonical"].rstrip("/")
        url = f"{canonical}/ImplementationGuide/{cfg['id']}"

        ig: Dict[str, Any] = {
            "resourceType": "ImplementationGuide",
            "id": cfg["id"],
            "url": url,
        }

        if cfg.get("version"):
            ig["version"] = cfg["version"]

        if cfg.get("title"):
            ig["name"] = cfg["title"].replace(" ", "")
            ig["title"] = cfg["title"]

        ig["status"] = cfg["status"]
        ig["fhirVersion"] = [cfg["fhirVersion"]]
        ig["packageId"] = cfg["id"]

        # definition
        definition: Dict[str, Any] = {}

        # definition.resource
        if self._resources:
            res_list = []
            for r in self._resources:
                entry: Dict[str, Any] = {
                    "reference": {"reference": f"{r['resourceType']}/{r['id']}"},
                }
                if r.get("name"):
                    entry["name"] = r["name"]
                if r.get("description"):
                    entry["description"] = r["description"]

                if r["isExample"]:
                    if r.get("exampleCanonical"):
                        entry["exampleCanonical"] = r["exampleCanonical"]
                    else:
                        entry["exampleBoolean"] = True
                else:
                    entry["exampleBoolean"] = False

                res_list.append(entry)
            definition["resource"] = res_list

        # definition.page (recursive)
        definition["page"] = self._page_node_to_r4(root_page)

        ig["definition"] = definition
        return ig

    def _page_node_to_r4(self, page: Dict) -> Dict[str, Any]:
        node: Dict[str, Any] = {
            "nameUrl": page["nameUrl"],
            "title": page["title"],
            "generation": page["generation"],
        }
        children = page.get("children", [])
        if children:
            node["page"] = [self._page_node_to_r4(c) for c in children]
        return node

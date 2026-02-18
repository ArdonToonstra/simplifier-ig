"""Validates Implementation Guide input structure for Simplifier.net publishing."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import new_validation_result
from .yaml_helpers import load_yaml

REQUIRED_INPUT_FOLDERS = ["resources", "examples", "pages", "styles", "pagetemplates-artifacts"]
OPTIONAL_INPUT_FOLDERS = ["images", "pagetemplates"]
REQUIRED_INPUT_FILES = ["guide.yaml"]
REQUIRED_STYLE_FILES = ["master.html", "settings.style", "style.css"]


class ValidationError(Exception):
    pass


class IGInputValidator:
    """Validates Implementation Guide input structure for Simplifier.net publishing."""

    def __init__(self, input_dir: str, log=None):
        self._input_dir = Path(input_dir).resolve()
        self._log = log or (lambda msg: None)

    # -- public --

    def validate(self) -> Dict[str, Any]:
        result = new_validation_result()

        try:
            # Step 1: input directory exists
            self._validate_input_directory()

            # Step 2: required folders
            self._validate_required_folders(result)

            # Step 3: required files
            self._validate_required_files(result)

            # Step 4: load guide.yaml
            result["guide_config"] = self._load_guide_config(result)

            # Step 5: determine guide name from url-key
            result["guide_name"] = self._determine_guide_name(result["guide_config"])

            # Step 6: load variables.yaml (optional)
            result["variables_config"] = self._load_variables_config(result)

            # Step 7: check optional folders
            self._check_optional_folders(result)

            # Step 8: validate styles structure
            self._validate_styles_structure(result)

            # Step 9: count files
            result["file_counts"] = self._count_files(result.get("custom_styles_folder"))

            # Step 10: check IG resource fields (informational)
            self._check_ig_resource_fields(result)

            result["is_valid"] = len(result["errors"]) == 0
        except ValidationError as e:
            result["errors"].append(str(e))
            result["is_valid"] = False

        return result

    # -- private --

    def _validate_input_directory(self):
        if not self._input_dir.exists():
            raise ValidationError(f"Input directory not found: {self._input_dir}")
        self._log(f"[INFO] Validating input directory: {self._input_dir}")

    def _validate_required_folders(self, result):
        self._log("[INFO] Checking required folders...")
        missing = [f for f in REQUIRED_INPUT_FOLDERS if not (self._input_dir / f).is_dir()]
        if missing:
            raise ValidationError(f"Missing required folders in input directory: {', '.join(missing)}")
        self._log(f"[OK] Found required folders: {', '.join(REQUIRED_INPUT_FOLDERS)}")

    def _validate_required_files(self, result):
        self._log("[INFO] Checking required files...")
        missing = [f for f in REQUIRED_INPUT_FILES if not (self._input_dir / f).is_file()]
        if missing:
            raise ValidationError(f"Missing required files in input directory: {', '.join(missing)}")
        self._log(f"[OK] Found required files: {', '.join(REQUIRED_INPUT_FILES)}")

    def _load_guide_config(self, result) -> Dict[str, Any]:
        self._log("[INFO] Loading guide.yaml...")
        config = load_yaml(self._input_dir / "guide.yaml")
        if not config:
            raise ValidationError("guide.yaml is empty")

        title = config.get("title")
        if not title or not str(title).strip():
            raise ValidationError("guide.yaml is missing required 'title' field")

        url_key = config.get("url-key")
        if not url_key or not str(url_key).strip():
            raise ValidationError(
                "guide.yaml is missing required 'url-key' field\n"
                "   This field is used to determine the output directory name"
            )

        style_name = config.get("style-name")
        if not style_name or not str(style_name).strip():
            raise ValidationError(
                "guide.yaml is missing required 'style-name' field\n"
                "   This field must match the name of the subfolder in styles/"
            )

        result["guide_title"] = str(title).strip()
        result["style_name"] = str(style_name).strip()
        self._log(f"[OK] Loaded guide.yaml - Title: {result['guide_title']}, Style: {result['style_name']}")
        return config

    def _determine_guide_name(self, guide_config: Dict) -> str:
        self._log("[INFO] Determining guide name from url-key...")
        guide_name = str(guide_config["url-key"]).strip()
        self._log(f"[OK] Guide name: {guide_name}")
        return guide_name

    def _load_variables_config(self, result) -> Optional[Dict]:
        self._log("[INFO] Looking for variables.yaml...")
        var_path = self._input_dir / "variables.yaml"
        if not var_path.exists():
            self._log("[INFO] variables.yaml not found (optional file)")
            return None
        config = load_yaml(var_path)
        if not config:
            self._log("[WARNING] variables.yaml is empty")
            return None
        self._log("[OK] Loaded variables.yaml")
        return config

    def _check_optional_folders(self, result):
        self._log("[INFO] Checking optional folders...")
        for folder in OPTIONAL_INPUT_FOLDERS:
            folder_path = self._input_dir / folder
            if not folder_path.exists():
                self._log(f"[INFO] Optional folder not found: {folder}")
                continue
            if folder == "images":
                result["has_images_folder"] = True
                count = sum(1 for _ in folder_path.rglob("*") if _.is_file())
                self._log(f"[OK] Found optional folder: {folder} ({count} files)")
            elif folder == "pagetemplates":
                md_files = list(folder_path.glob("*.md"))
                if not md_files:
                    result["warnings"].append(f"Optional folder '{folder}' is empty (no .md files found)")
                else:
                    self._log(f"[OK] Found optional folder: {folder} ({len(md_files)} template files)")

    def _validate_styles_structure(self, result):
        self._log("[INFO] Validating styles folder...")
        styles_dir = self._input_dir / "styles"
        if not styles_dir.is_dir():
            raise ValidationError(
                "Required folder not found: styles\n"
                "   This folder can be retrieved by downloading a Simplifier project that contains an IG."
            )

        style_name = result["style_name"]
        if not style_name:
            raise ValidationError("style-name not found in guide.yaml")

        custom_dir = styles_dir / style_name
        if not custom_dir.is_dir():
            raise ValidationError(
                f"Style folder not found: styles/{style_name}\n"
                f"   The folder name must match the 'style-name' value in guide.yaml"
            )

        result["custom_styles_folder"] = style_name
        self._log(f"[OK] Found styles folder: styles/{style_name}")

        missing = [f for f in REQUIRED_STYLE_FILES if not (custom_dir / f).is_file()]
        if missing:
            raise ValidationError(
                f"Missing required style files in styles/{style_name}: {', '.join(missing)}"
            )

        self._log(f"[OK] All required style files present: {', '.join(REQUIRED_STYLE_FILES)}")

    def _count_files(self, custom_styles_folder: Optional[str]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        res_dir = self._input_dir / "resources"
        counts["resources"] = len(list(res_dir.glob("*.json"))) if res_dir.is_dir() else 0

        ex_dir = self._input_dir / "examples"
        counts["examples"] = len(list(ex_dir.glob("*.json"))) if ex_dir.is_dir() else 0

        pages_dir = self._input_dir / "pages"
        counts["pages"] = len(list(pages_dir.rglob("*.md"))) if pages_dir.is_dir() else 0

        if custom_styles_folder:
            cs_dir = self._input_dir / "styles" / custom_styles_folder
            counts["styles"] = len(list(cs_dir.glob("*"))) if cs_dir.is_dir() else 0
        else:
            counts["styles"] = 0

        pt_dir = self._input_dir / "pagetemplates"
        counts["pagetemplates"] = len(list(pt_dir.glob("*.md"))) if pt_dir.is_dir() else 0
        return counts

    def _check_ig_resource_fields(self, result):
        self._log("[INFO] Checking for ImplementationGuide resource fields...")
        config = result["guide_config"]
        valid_statuses = {"draft", "active", "retired", "unknown"}
        missing: List[str] = []

        ig_id = config.get("id")
        if ig_id and str(ig_id).strip():
            result["ig_resource_id"] = str(ig_id).strip()
        else:
            missing.append("id")

        status = config.get("status")
        if status and str(status).strip():
            sv = str(status).strip().lower()
            if sv in valid_statuses:
                result["ig_resource_status"] = sv
            else:
                result["warnings"].append(
                    f"Invalid status value '{sv}' for IG resource generation. "
                    f"Must be one of: draft, active, retired, unknown"
                )
                missing.append("status (invalid value)")
        else:
            missing.append("status")

        fv = config.get("fhirVersion")
        if fv and str(fv).strip():
            result["ig_resource_fhir_version"] = str(fv).strip()
        else:
            missing.append("fhirVersion")

        canonical = config.get("canonical")
        if canonical and str(canonical).strip():
            result["ig_resource_canonical"] = str(canonical).strip()
        else:
            missing.append("canonical")

        result["has_ig_resource_fields"] = len(missing) == 0

        if result["has_ig_resource_fields"]:
            self._log("[OK] All ImplementationGuide resource fields present (id, status, fhirVersion, canonical)")
        else:
            self._log(f"[INFO] Missing IG resource fields: {', '.join(missing)}")
            self._log("[INFO] These fields are optional but required for IG resource generation")

"""Generates Implementation Guide structure for Simplifier.net publishing."""

import json
import re
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .models import new_generation_result
from .utils import is_subpath
from .validator import IGInputValidator
from .yaml_helpers import dump_yaml, load_yaml


class GenerationError(Exception):
    pass


class IGGenerator:
    """Generates Implementation Guide structure for Simplifier.net publishing."""

    def __init__(self, input_dir: str, output_dir: str, log=None):
        self._input_dir = Path(input_dir).resolve()
        self._output_dir = Path(output_dir).resolve()
        self._log = log or (lambda msg: None)
        self._guide_name = ""
        self._guide_output_dir: Optional[Path] = None
        self._guide_config: Optional[Dict] = None
        self._variables_config: Optional[Dict] = None
        self._templates: Dict[str, str] = {}
        self._templates_dir: Optional[Path] = None

    def generate(self, skip_validation: bool = False) -> Dict[str, Any]:
        result = new_generation_result()

        try:
            # Step 1: Validate input (unless skipped)
            if not skip_validation:
                self._log("=" * 70)
                self._log("[VALIDATE] Running input validation...")
                self._log("=" * 70)
                validator = IGInputValidator(str(self._input_dir), self._log)
                vr = validator.validate()
                if not vr["is_valid"]:
                    raise GenerationError(
                        "Input validation failed:\n" + "\n".join(vr["errors"])
                    )
                result["warnings"].extend(vr["warnings"])

            # Step 2: Load configurations
            self._load_guide_config()
            self._log(f"\n[TARGET] Generating IG: {self._guide_name}")
            self._load_variables_config()
            self._load_templates()

            # Step 3: Setup output directory
            self._setup_output_directory()
            result["guide_name"] = self._guide_name
            result["output_path"] = str(self._guide_output_dir)

            # Step 4: Copy root files
            self._copy_root_files()

            # Step 5: Transform and copy pages
            result["page_count"] = self._transform_pages()

            # Step 6: Copy pagetemplates if present
            self._copy_pagetemplates()

            # Step 7: Generate artifact pages
            resources_by_type, examples = self._generate_artifacts()
            result["resource_count"] = sum(len(v) for v in resources_by_type.values())
            result["example_count"] = len(examples)

            # Step 8: Copy artifact index pages
            index_pages = self._copy_artifact_index_pages()

            # Step 9: Generate toc.yaml files
            result["toc_files_generated"] = self._generate_toc_files()

            # Step 10: Generate artifacts toc
            self._generate_artifacts_toc(resources_by_type, examples, index_pages)

            result["success"] = True

            self._log("\n" + "=" * 70)
            self._log("[SUCCESS] IG Generation Complete!")
            self._log("=" * 70)
            self._log(f"\n[OUTPUT] Output location: {self._guide_output_dir}")

        except GenerationError:
            raise
        except Exception as e:
            raise GenerationError(f"Unexpected error during generation: {e}") from e

        return result

    # -- config loading --

    def _load_guide_config(self):
        config = load_yaml(self._input_dir / "guide.yaml")
        if not config:
            raise GenerationError("guide.yaml is empty or invalid")
        self._guide_config = config

        url_key = config.get("url-key")
        if not url_key:
            raise GenerationError("Could not find url-key in guide.yaml")
        self._guide_name = str(url_key).strip()
        if not self._guide_name:
            raise GenerationError("url-key is empty in guide.yaml")

        if "menu" in config:
            self._log("\n[MENU] Loaded menu configuration from guide.yaml")
        else:
            self._log("\n[WARNING] No menu configuration found in guide.yaml")

    def _load_variables_config(self):
        var_path = self._input_dir / "variables.yaml"
        if not var_path.exists():
            self._log("[INFO] variables.yaml not found (optional file)")
            return
        config = load_yaml(var_path)
        if not config:
            self._log("[WARNING] variables.yaml is empty")
            return
        self._variables_config = config
        self._log("[OK] Loaded variables.yaml")

    def _load_templates(self):
        self._log("\n[TEMPLATES] Loading page templates...")
        self._templates_dir = self._input_dir / "pagetemplates-artifacts"
        if not self._templates_dir.is_dir():
            self._log(f"[WARNING] Templates directory not found: {self._templates_dir}")
            return

        template_files = {
            "CodeSystem": "codesystem.md",
            "StructureDefinition": "structuredefinition.md",
            "ValueSet": "valueset.md",
            "Example": "examples.md",
        }
        for resource_type, template_file in template_files.items():
            tp = self._templates_dir / template_file
            if tp.is_file():
                self._templates[resource_type] = tp.read_text(encoding="utf-8")
                self._log(f"   Loaded template: {template_file}")

        self._log(f"[OK] Loaded {len(self._templates)} templates")

    # -- output setup --

    def _setup_output_directory(self):
        self._log("\n" + "=" * 70)
        self._log("[SETUP] Setting up output directory structure...")
        self._log("=" * 70)

        self._guide_output_dir = self._output_dir / self._guide_name

        if self._guide_output_dir.exists():
            self._log(f"[WARNING] Removing existing output directory: {self._guide_output_dir}")
            shutil.rmtree(self._guide_output_dir)

        self._guide_output_dir.mkdir(parents=True, exist_ok=True)
        self._log(f"[OK] Created output directory: {self._guide_output_dir}")

        home_dir = self._guide_output_dir / "Home"
        home_dir.mkdir(exist_ok=True)
        self._log(f"[OK] Created Home directory: {home_dir}")

    # -- copy root --

    def _copy_root_files(self):
        self._log("\n[COPY] Copying root configuration files...")

        guide_yaml = self._input_dir / "guide.yaml"
        if guide_yaml.is_file():
            shutil.copy2(guide_yaml, self._guide_output_dir / "guide.yaml")
            self._log("[OK] Copied guide.yaml")

        variables_yaml = self._input_dir / "variables.yaml"
        if variables_yaml.is_file():
            shutil.copy2(variables_yaml, self._guide_output_dir / "variables.yaml")
            self._log("[OK] Copied variables.yaml")

        styles_dir = self._input_dir / "styles"
        if styles_dir.is_dir():
            shutil.copytree(styles_dir, self._guide_output_dir / "styles")
            self._log("[OK] Copied styles directory")

        images_dir = self._input_dir / "images"
        if images_dir.is_dir():
            shutil.copytree(images_dir, self._guide_output_dir / "Home" / "images")
            self._log("[OK] Copied images directory")

    # -- pages --

    def _transform_pages(self) -> int:
        self._log("\n[TRANSFORM] Transforming and copying pages...")
        pages_dir = self._input_dir / "pages"
        home_dir = self._guide_output_dir / "Home"

        if not pages_dir.is_dir():
            raise GenerationError(f"Pages directory not found: {pages_dir}")

        file_count = 0
        for item in pages_dir.rglob("*"):
            if not item.is_file():
                continue
            relative = item.relative_to(pages_dir)

            if item.suffix.lower() == ".md":
                new_name = item.stem.lower() + ".page.md"
                out_path = home_dir / relative.parent / new_name
            else:
                out_path = home_dir / relative

            out_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, out_path)
            file_count += 1

        self._log(f"[OK] Transformed and copied {file_count} files")
        return file_count

    # -- pagetemplates --

    def _copy_pagetemplates(self):
        pt_dir = self._input_dir / "pagetemplates"
        if pt_dir.is_dir():
            self._log("\n[COPY] Copying page templates...")
            output_pt = self._guide_output_dir / "Home" / "pagetemplates"
            shutil.copytree(pt_dir, output_pt)
            count = len(list(output_pt.glob("*.md")))
            self._log(f"[OK] Copied {count} page templates")

    # -- FHIR resource parsing (JSON only) --

    @staticmethod
    def _parse_fhir_resource(file_path: Path) -> Optional[Dict[str, str]]:
        """Parse a FHIR JSON resource, returning {resourceType, id, filename, url} or None."""
        if file_path.suffix.lower() != ".json":
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                resource = json.load(f)
            rt = resource.get("resourceType")
            rid = resource.get("id")
            if not rt or not rid:
                return None
            return {
                "resourceType": rt,
                "id": rid,
                "filename": file_path.stem,
                "filepath": str(file_path),
                "url": resource.get("url", ""),
            }
        except Exception:
            return None

    # -- template variable resolution --

    @staticmethod
    def _resolve_template_variables(template: str, variables: Dict[str, str]) -> str:
        """Resolve {{ig-var: variable-name }} placeholders."""
        pattern = r"\{\{ig-var:\s*([^}]+)\s*\}\}"

        def _replace(m):
            var_name = m.group(1).strip()
            return variables.get(var_name, m.group(0))

        return re.sub(pattern, _replace, template)

    # -- artifacts --

    def _generate_artifacts(self) -> Tuple[Dict[str, List], List]:
        self._log("\n[ARTIFACTS] Generating artifact pages...")
        artifacts_dir = self._guide_output_dir / "Home" / "artifacts"
        artifacts_dir.mkdir(exist_ok=True)

        # Create artifacts index page
        (artifacts_dir / "index.page.md").write_text(
            "## {{page-title}}\n\n"
            "This section contains all the FHIR artifacts defined in this Implementation Guide.\n\n"
            "{{index:children}}\n",
            encoding="utf-8",
        )

        # Process resources
        resources_dir = self._input_dir / "resources"
        resources_by_type: Dict[str, List] = defaultdict(list)

        if resources_dir.is_dir():
            for rf in sorted(resources_dir.glob("*.json")):
                info = self._parse_fhir_resource(rf)
                if info:
                    resources_by_type[info["resourceType"]].append(info)

        resource_count = 0
        for resource_type in sorted(resources_by_type):
            resources = resources_by_type[resource_type]
            type_dir = artifacts_dir / resource_type.lower()
            type_dir.mkdir(exist_ok=True)

            template = self._templates.get(resource_type, "")

            for resource in resources:
                page_name = f"{resource['id']}.page.md"
                page_path = type_dir / page_name

                variables = {
                    "file-name": resource["id"],
                    f"{resource_type}.url": resource.get("url", ""),
                }

                if template:
                    content = self._resolve_template_variables(template, variables)
                else:
                    content = (
                        f"# {resource['id']}\n\n"
                        f"*Resource Type: {resource_type}*\n\n"
                        f"<!-- No template found for {resource_type} -->\n"
                    )

                page_path.write_text(content, encoding="utf-8")
                resource_count += 1

            self._log(f"   Created {len(resources)} {resource_type} artifact pages")

        # Process examples
        examples_dir = self._input_dir / "examples"
        examples_list: List[Dict] = []

        if examples_dir.is_dir():
            examples_artifact_dir = artifacts_dir / "examples"
            examples_artifact_dir.mkdir(exist_ok=True)

            example_template = self._templates.get("Example", "")

            for ef in sorted(examples_dir.glob("*.json")):
                info = self._parse_fhir_resource(ef)
                if info:
                    examples_list.append(info)
                    page_name = f"{info['id']}.page.md"
                    page_path = examples_artifact_dir / page_name

                    variables = {
                        "file-name": info["id"],
                        "Resource.id": info["id"],
                        "ResourceType/Resource.id": f"{info['resourceType']}/{info['id']}",
                    }

                    if example_template:
                        content = self._resolve_template_variables(example_template, variables)
                    else:
                        content = (
                            f"# {info['id']}\n\n"
                            f"*Example of {info['resourceType']}*\n\n"
                            f"<!-- No template found for examples -->\n"
                        )

                    page_path.write_text(content, encoding="utf-8")

            if examples_list:
                self._log(f"   Created {len(examples_list)} example artifact pages")

        self._log(f"[OK] Generated {resource_count + len(examples_list)} artifact pages")
        return dict(resources_by_type), examples_list

    def _copy_artifact_index_pages(self) -> Dict[str, bool]:
        self._log("\n[ARTIFACTS] Copying artifact index pages...")
        index_pages: Dict[str, bool] = {}

        if not self._templates_dir or not self._templates_dir.is_dir():
            self._log("[WARNING] Templates directory not found, skipping index pages")
            return index_pages

        artifacts_dir = self._guide_output_dir / "Home" / "artifacts"

        for index_file in sorted(self._templates_dir.glob("*.index.md")):
            resource_type = index_file.stem.replace(".index", "")
            target_dir = artifacts_dir / resource_type
            target_dir.mkdir(parents=True, exist_ok=True)

            target_file = target_dir / "index.page.md"
            shutil.copy2(index_file, target_file)
            index_pages[resource_type] = True
            self._log(f"   Copied {index_file.name} -> {resource_type}/index.page.md")

        if index_pages:
            self._log(f"[OK] Copied {len(index_pages)} artifact index pages")
        else:
            self._log("[INFO] No artifact index pages found")

        return index_pages

    # -- TOC generation --

    def _write_toc_file(self, path: Path, entries: List[Dict[str, str]]):
        dump_yaml(entries, path)

    def _generate_toc_files(self) -> int:
        self._log("\n[TOC] Generating table of contents files...")

        # Root toc.yaml
        root_toc = [{"name": "Home", "filename": "Home"}]
        self._write_toc_file(self._guide_output_dir / "toc.yaml", root_toc)
        self._log("[OK] Generated root toc.yaml")

        # Home/toc.yaml from menu config
        self._generate_home_toc()

        toc_count = 2  # root + home

        # Subdirectory toc.yaml (skip pagetemplates and artifacts subtree)
        home_dir = self._guide_output_dir / "Home"
        artifacts_path = home_dir / "artifacts"

        for current_dir in sorted(home_dir.rglob("*")):
            if not current_dir.is_dir():
                continue
            dir_name = current_dir.name

            # Skip pagetemplates and anything under artifacts
            if dir_name == "pagetemplates":
                continue
            if is_subpath(current_dir, artifacts_path):
                continue

            entries = self._generate_toc_for_directory(current_dir)
            if entries:
                self._write_toc_file(current_dir / "toc.yaml", entries)
                rel = current_dir.relative_to(self._guide_output_dir)
                self._log(f"   Generated {rel}/toc.yaml ({len(entries)} entries)")
                toc_count += 1

        self._log(f"[OK] Generated {toc_count} toc.yaml files")
        return toc_count

    def _generate_home_toc(self):
        home_dir = self._guide_output_dir / "Home"
        home_toc: List[Dict[str, str]] = []

        menu = self._guide_config.get("menu") if self._guide_config else None
        if isinstance(menu, dict):
            for display_name, value in menu.items():
                display_name = str(display_name)

                if isinstance(value, bool) and value:
                    folder_name = display_name.lower()
                    if (home_dir / folder_name).is_dir():
                        home_toc.append({"name": display_name, "filename": folder_name})

                elif isinstance(value, str):
                    if value.lower().endswith(".md"):
                        page_name = value.replace(".md", ".page.md")
                        if (home_dir / page_name).is_file():
                            home_toc.append({"name": display_name, "filename": page_name})
                    else:
                        if (home_dir / value).is_dir():
                            home_toc.append({"name": display_name, "filename": value})

            if home_toc:
                self._write_toc_file(home_dir / "toc.yaml", home_toc)
                self._log(f"   Generated Home/toc.yaml ({len(home_toc)} entries) from menu config")
        else:
            self._log("   [WARNING] No menu config found, using auto-generation")
            entries = self._generate_toc_for_directory(home_dir)
            if entries:
                self._write_toc_file(home_dir / "toc.yaml", entries)
                self._log(f"   Generated Home/toc.yaml ({len(entries)} entries)")

    def _generate_toc_for_directory(self, directory: Path) -> List[Dict[str, str]]:
        entries: List[Dict[str, str]] = []
        files: List[Path] = []
        dirs: List[Path] = []

        for item in directory.iterdir():
            name = item.name
            if name == "toc.yaml" or name == "pagetemplates":
                continue
            if item.is_file() and name.endswith(".page.md"):
                files.append(item)
            elif item.is_dir() and not name.startswith(".") and not name.startswith("_"):
                dirs.append(item)

        # Sort: index first, then alphabetical
        files.sort(key=lambda f: (0 if f.name.lower() == "index.page.md" else 1, f.name))
        dirs.sort(key=lambda d: d.name)

        for f in files:
            stem = f.name.replace(".page.md", "")
            if stem.lower() == "index":
                display = "Index"
            else:
                display = stem.replace("-", " ").title()
            entries.append({"name": display, "filename": f.name})

        for d in dirs:
            dn = d.name
            if dn.lower() == "artifacts":
                display = "Artifacts"
            else:
                display = dn.replace("-", " ").title()
            entries.append({"name": display, "filename": dn})

        return entries

    def _generate_artifacts_toc(
        self,
        resources_by_type: Dict[str, List],
        examples_list: List,
        index_pages: Dict[str, bool],
    ):
        self._log("\n[TOC] Generating Artifacts table of contents...")
        artifacts_dir = self._guide_output_dir / "Home" / "artifacts"

        # Main artifacts toc
        artifacts_toc: List[Dict[str, str]] = []
        if (artifacts_dir / "index.page.md").is_file():
            artifacts_toc.append({"name": "Index", "filename": "index.page.md"})

        for rt in sorted(resources_by_type):
            artifacts_toc.append({"name": rt, "filename": rt.lower()})

        if examples_list:
            artifacts_toc.append({"name": "Examples", "filename": "examples"})

        self._write_toc_file(artifacts_dir / "toc.yaml", artifacts_toc)
        self._log("   Generated artifacts/toc.yaml")

        # Per resource type
        for rt in sorted(resources_by_type):
            resources = resources_by_type[rt]
            type_dir = artifacts_dir / rt.lower()
            type_toc: List[Dict[str, str]] = []

            if index_pages.get(rt.lower()):
                type_toc.append({"name": "Index", "filename": "index.page.md"})

            for resource in sorted(resources, key=lambda r: r["id"]):
                type_toc.append({"name": resource["id"], "filename": f"{resource['id']}.page.md"})

            self._write_toc_file(type_dir / "toc.yaml", type_toc)
            self._log(f"   Generated artifacts/{rt.lower()}/toc.yaml ({len(type_toc)} entries)")

        # Examples
        if examples_list:
            ex_dir = artifacts_dir / "examples"
            ex_toc: List[Dict[str, str]] = []

            if index_pages.get("examples"):
                ex_toc.append({"name": "Index", "filename": "index.page.md"})

            for ex in sorted(examples_list, key=lambda e: e["id"]):
                ex_toc.append({"name": ex["id"], "filename": f"{ex['id']}.page.md"})

            self._write_toc_file(ex_dir / "toc.yaml", ex_toc)
            self._log(f"   Generated artifacts/examples/toc.yaml ({len(ex_toc)} entries)")

        self._log("[OK] Generated Artifacts table of contents")

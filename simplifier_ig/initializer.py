"""Initializes a new IG input folder structure with template files."""

import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .yaml_helpers import load_yaml


class IGInitializer:
    """Initializes a new IG input folder structure with template files."""

    REQUIRED_FOLDERS = ["resources", "examples", "pages", "pagetemplates-artifacts"]
    OPTIONAL_FOLDERS = ["images", "pagetemplates"]

    def __init__(self, output_dir: str, guide_name: str, style_name: str = "custom", log=None):
        self._output_dir = Path(output_dir).resolve()
        self._guide_name = guide_name
        self._style_name = style_name
        self._log = log or (lambda msg: None)

    def initialize(self, force: bool = False) -> Dict[str, Any]:
        result = {
            "success": False,
            "output_path": str(self._output_dir),
            "folders_created": 0,
            "files_created": 0,
            "warnings": [],
            "errors": [],
        }

        try:
            # Check existing directory
            if self._output_dir.exists():
                entries = list(self._output_dir.iterdir())
                if entries and not force:
                    result["errors"].append(f"Directory is not empty: {self._output_dir}")
                    result["errors"].append("Use --force to initialize anyway (existing files will not be overwritten).")
                    return result
                if entries:
                    result["warnings"].append("Directory is not empty. Existing files will not be overwritten.")

            self._log("=" * 70)
            self._log("[INIT] Initializing IG input folder structure...")
            self._log("=" * 70)
            self._log(f"Output folder: {self._output_dir}")
            self._log(f"Guide name: {self._guide_name}")
            self._log(f"Style name: {self._style_name}")
            self._log("")

            # Create main directory
            self._output_dir.mkdir(parents=True, exist_ok=True)

            # Create required folders
            self._log("[FOLDERS] Creating required folders...")
            for folder in self.REQUIRED_FOLDERS:
                fp = self._output_dir / folder
                if not fp.exists():
                    fp.mkdir(parents=True, exist_ok=True)
                    self._log(f"   Created: {folder}/")
                    result["folders_created"] += 1
                else:
                    self._log(f"   Exists: {folder}/")

            # Create optional folders
            self._log("\n[FOLDERS] Creating optional folders...")
            for folder in self.OPTIONAL_FOLDERS:
                fp = self._output_dir / folder
                if not fp.exists():
                    fp.mkdir(parents=True, exist_ok=True)
                    self._log(f"   Created: {folder}/")
                    result["folders_created"] += 1
                else:
                    self._log(f"   Exists: {folder}/")

            # Create styles folder
            styles_folder = self._output_dir / "styles" / self._style_name
            if not styles_folder.exists():
                styles_folder.mkdir(parents=True, exist_ok=True)
                self._log(f"   Created: styles/{self._style_name}/")
                result["folders_created"] += 1
            else:
                self._log(f"   Exists: styles/{self._style_name}/")

            # Copy template files
            self._log("\n[FILES] Copying template files...")
            template_base = self._get_template_base_path()

            if template_base:
                result["files_created"] += self._copy_template_files(template_base, result["warnings"])
            else:
                result["warnings"].append("Template files not found. Creating minimal configuration.")
                result["files_created"] += self._create_minimal_files()

            # Customize guide.yaml
            self._customize_guide_yaml()

            result["success"] = True

            self._log("\n" + "=" * 70)
            self._log("[SUCCESS] IG Input Structure Initialized!")
            self._log("=" * 70)
            self._log(f"\n[OUTPUT] Location: {self._output_dir}")
            self._log(f"[STATS] Created {result['folders_created']} folders, {result['files_created']} files")
            self._log("\n[NEXT STEPS]")
            self._log("   1. Add your FHIR resources to resources/")
            self._log("   2. Add example resources to examples/")
            self._log("   3. Add documentation pages to pages/")
            self._log("   4. Edit guide.yaml to configure your menu")
            self._log("   5. Run 'simplifier-ig validate' to validate the structure")
            self._log("   6. Run 'simplifier-ig generate' to create the IG output")

        except Exception as e:
            result["errors"].append(f"Initialization failed: {e}")

        return result

    def _get_template_base_path(self) -> Optional[Path]:
        """Find the bundled templates directory.

        Supports both normal installs (``Path(__file__).parent / "templates"``)
        and PyInstaller frozen binaries (``sys._MEIPASS / "templates"``).
        """
        # PyInstaller frozen binary
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            tp = Path(meipass) / "templates"
            if tp.is_dir():
                return tp

        # Normal install — templates live next to this module
        tp = Path(__file__).parent / "templates"
        if tp.is_dir():
            return tp

        return None

    def _copy_template_files(self, template_base: Path, warnings: List[str]) -> int:
        count = 0

        # Root files
        count += self._copy_template_file(template_base, "guide.yaml", self._output_dir, warnings)
        count += self._copy_template_file(template_base, "variables.yaml", self._output_dir, warnings)

        # pages/
        pages_tp = template_base / "pages"
        pages_out = self._output_dir / "pages"
        if pages_tp.is_dir():
            for f in pages_tp.iterdir():
                if f.is_file():
                    count += self._copy_template_file(pages_tp, f.name, pages_out, warnings)

        # pagetemplates-artifacts/
        art_tp = template_base / "pagetemplates-artifacts"
        art_out = self._output_dir / "pagetemplates-artifacts"
        if art_tp.is_dir():
            for f in art_tp.iterdir():
                if f.is_file():
                    count += self._copy_template_file(art_tp, f.name, art_out, warnings)

        # pagetemplates/
        pt_tp = template_base / "pagetemplates"
        pt_out = self._output_dir / "pagetemplates"
        if pt_tp.is_dir():
            for f in pt_tp.iterdir():
                if f.is_file():
                    count += self._copy_template_file(pt_tp, f.name, pt_out, warnings)

        # styles — copy from template's first style folder into styles/{style_name}/
        styles_tp = template_base / "styles"
        if styles_tp.is_dir():
            style_folders = [d for d in styles_tp.iterdir() if d.is_dir()]
            if style_folders:
                source_style = style_folders[0]
                style_out = self._output_dir / "styles" / self._style_name
                for f in source_style.iterdir():
                    if f.is_file():
                        count += self._copy_template_file(source_style, f.name, style_out, warnings)

        return count

    def _copy_template_file(
        self, source_dir: Path, filename: str, dest_dir: Path, warnings: List[str]
    ) -> int:
        src = source_dir / filename
        dst = dest_dir / filename
        if not src.is_file():
            return 0
        if dst.is_file():
            self._log(f"   Skipped (exists): {dst.relative_to(self._output_dir)}")
            return 0
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        self._log(f"   Created: {dst.relative_to(self._output_dir)}")
        return 1

    def _create_minimal_files(self) -> int:
        count = 0

        # guide.yaml
        guide_path = self._output_dir / "guide.yaml"
        if not guide_path.is_file():
            url_key = self._guide_name.lower().replace(" ", "-")
            guide_path.write_text(
                f"# Implementation Guide Configuration\n"
                f"title: {self._guide_name}\n"
                f"url-key: {url_key}\n"
                f"style-name: {self._style_name}\n"
                f"\n"
                f"menu:\n"
                f"  Home: index.md\n"
                f"  Artifacts: artifacts\n",
                encoding="utf-8",
            )
            self._log("   Created: guide.yaml")
            count += 1

        # pages/index.md
        index_path = self._output_dir / "pages" / "index.md"
        if not index_path.is_file():
            index_path.parent.mkdir(parents=True, exist_ok=True)
            index_path.write_text(
                "# {{page-title}}\n\n"
                "Welcome to this FHIR Implementation Guide.\n\n"
                "## Overview\n\n"
                "This Implementation Guide defines the FHIR resources "
                "and constraints for your use case.\n",
                encoding="utf-8",
            )
            self._log("   Created: pages/index.md")
            count += 1

        # styles
        master_path = self._output_dir / "styles" / self._style_name / "master.html"
        if not master_path.is_file():
            master_path.parent.mkdir(parents=True, exist_ok=True)
            master_path.write_text(
                '<!DOCTYPE html>\n'
                '<html lang="en">\n'
                '<head>\n'
                '    <meta charset="UTF-8">\n'
                '    <title>{{page-title}} - {{guide-title}}</title>\n'
                f'    <link rel="stylesheet" href="{{{{root}}}}/styles/{self._style_name}/style.css">\n'
                '</head>\n'
                '<body>\n'
                '    <header><h1>{{guide-title}}</h1><nav>{{menu}}</nav></header>\n'
                '    <main><aside>{{toc}}</aside><article>{{content}}</article></main>\n'
                '</body>\n'
                '</html>',
                encoding="utf-8",
            )
            self._log(f"   Created: styles/{self._style_name}/master.html")
            count += 1

        settings_path = self._output_dir / "styles" / self._style_name / "settings.style"
        if not settings_path.is_file():
            settings_path.write_text(f"name: {self._style_name}\nversion: 1.0.0\n", encoding="utf-8")
            self._log(f"   Created: styles/{self._style_name}/settings.style")
            count += 1

        css_path = self._output_dir / "styles" / self._style_name / "style.css"
        if not css_path.is_file():
            css_path.write_text("/* Add your custom styles here */\n", encoding="utf-8")
            self._log(f"   Created: styles/{self._style_name}/style.css")
            count += 1

        # Minimal artifact page templates
        template_types = {
            "structuredefinition.md": "# {{page-title}}\n\n{{tree:{{ig-var: file-name }}}}\n\n{{render:{{ig-var: file-name }}}}\n",
            "valueset.md": "# {{page-title}}\n\n{{render:{{ig-var: file-name }}}}\n",
            "codesystem.md": "# {{page-title}}\n\n{{render:{{ig-var: file-name }}}}\n",
            "examples.md": "# {{page-title}}\n\n{{render:{{ig-var: file-name }}}}\n",
        }
        for fn, content in template_types.items():
            tp = self._output_dir / "pagetemplates-artifacts" / fn
            if not tp.is_file():
                tp.parent.mkdir(parents=True, exist_ok=True)
                tp.write_text(content, encoding="utf-8")
                self._log(f"   Created: pagetemplates-artifacts/{fn}")
                count += 1

        return count

    def _customize_guide_yaml(self):
        guide_path = self._output_dir / "guide.yaml"
        if not guide_path.is_file():
            return
        content = guide_path.read_text(encoding="utf-8")
        url_key = self._guide_name.lower().replace(" ", "-")
        content = content.replace("title: My Implementation Guide", f"title: {self._guide_name}")
        content = content.replace("url-key: my-implementation-guide", f"url-key: {url_key}")
        content = content.replace("style-name: custom", f"style-name: {self._style_name}")
        guide_path.write_text(content, encoding="utf-8")

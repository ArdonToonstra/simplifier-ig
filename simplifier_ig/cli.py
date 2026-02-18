"""CLI entry point for Simplifier.net IG tool."""

import argparse
import os
import sys

from .config import load_config, save_config
from .generator import GenerationError, IGGenerator
from .ig_resource import IGResourceGenerator
from .initializer import IGInitializer
from .validator import IGInputValidator


def _printer(msg: str):
    """Default log function that prints to stdout."""
    print(msg)


# ---------------------------------------------------------------------------
# Sub-command handlers
# ---------------------------------------------------------------------------

def cmd_init(args):
    path = args.path or os.path.join(os.getcwd(), "input")
    path = os.path.abspath(path)
    guide_name = args.name or "My Implementation Guide"
    style_name = args.style or "custom"

    _printer("=" * 70)
    _printer("Simplifier.net IG Input Initialization")
    _printer("=" * 70)
    _printer(f"Output folder: {path}")
    _printer(f"Guide name: {guide_name}")
    _printer(f"Style name: {style_name}")
    _printer("")

    init = IGInitializer(path, guide_name, style_name, _printer)
    result = init.initialize(force=args.force)

    for w in result["warnings"]:
        _printer(f"[WARNING] {w}")

    if not result["success"]:
        _printer("")
        _printer("Initialization failed:")
        for e in result["errors"]:
            _printer(f"  - {e}")
        return 1

    # Save path to config
    cfg = load_config()
    cfg["InputPath"] = path
    save_config(cfg)

    _printer("")
    _printer("IG input structure initialized successfully!")
    _printer(f"Created {result['folders_created']} folders and {result['files_created']} files.")
    _printer("Input path saved to project context.")
    return 0


def cmd_validate(args):
    path = args.input or os.path.join(os.getcwd(), "input")
    path = os.path.abspath(path)

    _printer("=" * 70)
    _printer("Simplifier.net IG Input Validation")
    _printer("=" * 70)
    _printer(f"Input folder: {path}")
    _printer("")

    validator = IGInputValidator(path, _printer)
    result = validator.validate()

    for w in result["warnings"]:
        _printer(f"[WARNING] {w}")

    if not result["is_valid"]:
        _printer("")
        _printer("Validation failed:")
        for e in result["errors"]:
            _printer(f"  - {e}")
        return 1

    # Display file counts
    _printer("")
    _printer("Input file counts:")
    fc = result["file_counts"]
    _printer(f"   - Resources: {fc.get('resources', 0)} files")
    _printer(f"   - Examples: {fc.get('examples', 0)} files")
    _printer(f"   - Pages: {fc.get('pages', 0)} files")
    _printer(f"   - Style files: {fc.get('styles', 0)} files")
    if fc.get("pagetemplates", 0) > 0:
        _printer(f"   - Page templates: {fc['pagetemplates']} files")

    # Save path to config
    cfg = load_config()
    cfg["InputPath"] = path
    save_config(cfg)

    _printer("")
    _printer(f"Validation complete - input structure is valid")
    _printer(f"Guide name: {result['guide_name']}")
    _printer("Input path saved to project context.")
    return 0


def cmd_generate(args):
    # Determine input path
    if args.input:
        input_path = os.path.abspath(args.input)
    else:
        cfg = load_config()
        input_path = cfg.get("InputPath")
        if not input_path:
            _printer("No input path specified.")
            _printer("Either run 'simplifier-ig validate <path>' first, or specify --input <path>")
            return 1
        _printer(f"Using saved input path: {input_path}")

    # Determine whether to generate IG resource (default: yes)
    generate_ig_resource = not args.no_ig_resource

    # Validate --ig-resource prerequisites (warn & skip if fields missing)
    if generate_ig_resource:
        is_valid, errors = IGResourceGenerator.validate_guide_yaml_for_ig_resource(input_path)
        if not is_valid:
            _printer("[WARNING] Cannot generate ImplementationGuide resource (missing fields in guide.yaml):")
            for e in errors:
                _printer(f"  - {e}")
            _printer("")
            _printer("[WARNING] Skipping IG resource generation. To add it later, ensure guide.yaml contains:")
            _printer("   id: <unique.id.for.ig>")
            _printer("   status: draft | active | retired | unknown")
            _printer("   fhirVersion: <version, e.g., 4.0.1>")
            _printer("   canonical: <canonical base URL>")
            _printer("")
            generate_ig_resource = False

    # Determine output path
    if args.output:
        output_path = os.path.abspath(args.output)
    else:
        cfg = load_config()
        output_folder = cfg.get("DefaultOutputFolder", "guides")
        output_path = os.path.join(os.getcwd(), output_folder)

    _printer("=" * 70)
    _printer("Simplifier.net IG Generation")
    _printer("=" * 70)
    _printer(f"Input: {input_path}")
    _printer(f"Output: {output_path}")
    if generate_ig_resource:
        _printer("ImplementationGuide resource: Yes")
    _printer("")

    try:
        generator = IGGenerator(input_path, output_path, _printer)
        result = generator.generate(skip_validation=args.skip_validation)

        for w in result["warnings"]:
            _printer(f"[WARNING] {w}")

        _printer("")
        _printer("IG Generation Complete!")
        _printer(f"Guide: {result['guide_name']}")
        _printer(f"Output: {result['output_path']}")
        _printer(f"Resources: {result['resource_count']}, Examples: {result['example_count']}, Pages: {result['page_count']}")
        _printer(f"TOC files generated: {result['toc_files_generated']}")

        # Generate IG resource (default behaviour)
        if generate_ig_resource:
            _printer("")
            _printer("Generating ImplementationGuide resource...")
            ig_gen = IGResourceGenerator(result["output_path"], input_path, _printer)
            ig_result = ig_gen.generate()

            if ig_result["success"]:
                _printer(f"Generated ImplementationGuide.json ({ig_result['page_count']} pages)")
            else:
                _printer("Failed to generate ImplementationGuide resource:")
                for e in ig_result["errors"]:
                    _printer(f"  - {e}")

        return 0

    except GenerationError as e:
        _printer(f"Generation failed: {e}")
        return 1


def cmd_ig_resource(args):
    # Determine guide output path
    if args.path:
        guide_output_path = os.path.abspath(args.path)
    else:
        cfg = load_config()
        guides_folder = os.path.join(os.getcwd(), cfg.get("DefaultOutputFolder", "guides"))
        if not os.path.isdir(guides_folder):
            _printer("No guides folder found. Run 'simplifier-ig generate' first.")
            return 1

        guide_folders = [
            os.path.join(guides_folder, d)
            for d in os.listdir(guides_folder)
            if os.path.isdir(os.path.join(guides_folder, d))
        ]

        if not guide_folders:
            _printer("No generated IGs found in guides folder. Run 'simplifier-ig generate' first.")
            return 1
        if len(guide_folders) == 1:
            guide_output_path = guide_folders[0]
        else:
            _printer("Multiple IGs found in guides folder. Please specify the path:")
            for gf in guide_folders:
                _printer(f"   {gf}")
            return 1

    if not os.path.isdir(guide_output_path):
        _printer(f"IG output folder not found: {guide_output_path}")
        return 1

    _printer("=" * 70)
    _printer("ImplementationGuide Resource Generation")
    _printer("=" * 70)
    _printer(f"IG Output: {guide_output_path}")
    _printer("")

    # Get input path
    input_path = args.input
    if not input_path:
        cfg = load_config()
        input_path = cfg.get("InputPath")

    ig_gen = IGResourceGenerator(guide_output_path, input_path, _printer)
    result = ig_gen.generate()

    if result["success"]:
        _printer("")
        _printer("ImplementationGuide resource generated successfully!")
        _printer(f"Output: {result['output_path']}")
        _printer(f"Pages: {result['page_count']}")
        return 0
    else:
        _printer("Generation failed:")
        for e in result["errors"]:
            _printer(f"  - {e}")
        return 1


def cmd_config(args):
    cfg = load_config()
    _printer("IG Configuration")
    _printer("-" * 40)
    _printer(f"Input path: {cfg.get('InputPath', '(not set)')}")
    _printer(f"Default output folder: {cfg.get('DefaultOutputFolder', 'guides')}")

    input_path = cfg.get("InputPath")
    if input_path and os.path.isdir(input_path):
        _printer("")
        _printer("Input folder exists and is accessible.")
        guide_yaml = os.path.join(input_path, "guide.yaml")
        variables_yaml = os.path.join(input_path, "variables.yaml")
        if os.path.isfile(guide_yaml) and os.path.isfile(variables_yaml):
            _printer("Required configuration files are present.")
        else:
            if not os.path.isfile(guide_yaml):
                _printer("[WARNING] guide.yaml not found in input folder")
            if not os.path.isfile(variables_yaml):
                _printer("[WARNING] variables.yaml not found in input folder")
    elif input_path:
        _printer(f"[WARNING] Input path does not exist: {input_path}")

    return 0


def cmd_clear(args):
    cfg = load_config()
    cfg.pop("InputPath", None)
    save_config(cfg)
    _printer("IG configuration cleared.")
    return 0


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="simplifier-ig",
        description="Simplifier.net IG CLI Tool — generate Implementation Guide structures",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # -- init --
    p_init = subparsers.add_parser("init", help="Initialize a new IG input folder structure")
    p_init.add_argument("--path", type=str, default=None, help="Path where the IG input structure will be created (default: ./input)")
    p_init.add_argument("--name", type=str, default=None, help="Name for the Implementation Guide (default: 'My Implementation Guide')")
    p_init.add_argument("--style", type=str, default=None, help="Name of the style folder to create (default: 'custom')")
    p_init.add_argument("--force", action="store_true", help="Allow initialization in a non-empty directory")

    # -- validate --
    p_validate = subparsers.add_parser("validate", help="Validate and set the IG input folder")
    p_validate.add_argument("--input", type=str, default=None, help="Path to the input folder (default: ./input)")

    # -- generate --
    p_generate = subparsers.add_parser("generate", help="Generate a Simplifier-compliant IG from input folder")
    p_generate.add_argument("--input", type=str, default=None, help="Path to the input folder (optional if previously set)")
    p_generate.add_argument("--output", type=str, default=None, help="Path to the output folder (default: ./guides)")
    p_generate.add_argument("--skip-validation", action="store_true", help="Skip input validation")
    p_generate.add_argument(
        "--no-ig-resource",
        action="store_true",
        help="Do NOT generate an ImplementationGuide.json resource file (generated by default)",
    )

    # -- ig-resource --
    p_ig_resource = subparsers.add_parser("ig-resource", help="Generate an ImplementationGuide.json resource from IG output")
    p_ig_resource.add_argument("--path", type=str, default=None, help="Path to the generated IG output folder")
    p_ig_resource.add_argument("--input", type=str, default=None, help="Path to the input folder (for resource collection)")

    # -- config --
    subparsers.add_parser("config", help="Show current IG configuration")

    # -- clear --
    subparsers.add_parser("clear", help="Clear saved IG configuration")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    dispatch = {
        "init": cmd_init,
        "validate": cmd_validate,
        "generate": cmd_generate,
        "ig-resource": cmd_ig_resource,
        "config": cmd_config,
        "clear": cmd_clear,
    }

    try:
        return dispatch[args.command](args)
    except KeyboardInterrupt:
        _printer("\n\n[CANCELLED] Operation cancelled by user")
        return 130
    except Exception as e:
        _printer(f"\n[ERROR] Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

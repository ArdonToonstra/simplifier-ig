"""Factory functions for result dictionaries."""

from typing import Any, Dict


def new_validation_result() -> Dict[str, Any]:
    return {
        "is_valid": False,
        "guide_name": "",
        "guide_title": "",
        "style_name": "",
        "has_images_folder": False,
        "guide_config": {},
        "variables_config": None,
        "custom_styles_folder": None,
        "file_counts": {},
        "warnings": [],
        "errors": [],
        "has_ig_resource_fields": False,
        "ig_resource_id": None,
        "ig_resource_canonical": None,
        "ig_resource_fhir_version": None,
        "ig_resource_status": None,
    }


def new_generation_result() -> Dict[str, Any]:
    return {
        "success": False,
        "output_path": "",
        "guide_name": "",
        "resource_count": 0,
        "example_count": 0,
        "page_count": 0,
        "toc_files_generated": 0,
        "warnings": [],
    }

import ast
import os
import sys
from pathlib import Path

import requests


REPO_ROOT = Path(__file__).resolve().parent.parent
COMMON_PATH = REPO_ROOT / "common.py"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"


def _extract_model_catalogue_node():
    source = COMMON_PATH.read_text(encoding="utf-8")
    module = ast.parse(source, filename=str(COMMON_PATH))

    for node in module.body:
        if not isinstance(node, ast.ClassDef) or node.name != "Shared":
            continue

        for child in node.body:
            if not isinstance(child, ast.Assign):
                continue

            for target in child.targets:
                if isinstance(target, ast.Name) and target.id == "MODEL_CATALOGUE":
                    return child.value

    raise RuntimeError("Could not find Shared.MODEL_CATALOGUE in common.py")


def _extract_string(node, context):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value

    raise RuntimeError(f"Unsupported {context}: {ast.dump(node, include_attributes=False)}")


def _extract_parameter_info(node):
    if node is None:
        return {"has_api_url": False, "base_model": None}

    if not isinstance(node, ast.Dict):
        raise RuntimeError(f"Unsupported parameter block: {ast.dump(node, include_attributes=False)}")

    has_api_url = False
    base_model = None

    for key_node, value_node in zip(node.keys, node.values):
        if not isinstance(key_node, ast.Constant) or not isinstance(key_node.value, str):
            continue

        if key_node.value == "api_url":
            has_api_url = True
        elif key_node.value == "base_model":
            base_model = _extract_string(value_node, "base_model")

    return {"has_api_url": has_api_url, "base_model": base_model}


def _extract_openrouter_routed_models():
    model_catalogue = _extract_model_catalogue_node()

    if not isinstance(model_catalogue, (ast.List, ast.Tuple)):
        raise RuntimeError("Shared.MODEL_CATALOGUE is not a list or tuple literal")

    routed_models = set()

    for item in model_catalogue.elts:
        if isinstance(item, ast.Constant) and isinstance(item.value, str):
            model_name = item.value
            if not model_name[:1].isupper():
                routed_models.add(model_name)
            continue

        if isinstance(item, ast.Tuple) and item.elts:
            model_name = _extract_string(item.elts[0], "model name")
            parameter_info = _extract_parameter_info(item.elts[1] if len(item.elts) > 1 else None)

            if parameter_info["has_api_url"]:
                continue

            if model_name[:1].isupper():
                continue

            routed_model_name = parameter_info["base_model"] or model_name
            if not routed_model_name[:1].isupper():
                routed_models.add(routed_model_name)
            continue

        raise RuntimeError(f"Unsupported MODEL_CATALOGUE entry: {ast.dump(item, include_attributes=False)}")

    return sorted(routed_models)


def _fetch_openrouter_model_ids():
    headers = {}
    api_key = os.getenv("OPENROUTER_API_KEY")

    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    response = requests.get(
        OPENROUTER_MODELS_URL,
        headers=headers,
        params={"output_modalities": "text"},
        timeout=60,
    )

    if response.status_code in {401, 403} and not api_key:
        raise RuntimeError("OpenRouter rejected an unauthenticated models request; set OPENROUTER_API_KEY.")

    response.raise_for_status()

    payload = response.json()
    if "data" not in payload or not isinstance(payload["data"], list):
        raise RuntimeError("Unexpected response from OpenRouter models API")

    return {
        item["id"]
        for item in payload["data"]
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }


def main():
    common_models = _extract_openrouter_routed_models()
    openrouter_models = _fetch_openrouter_model_ids()
    missing_models = [model_name for model_name in common_models if model_name not in openrouter_models]

    if not missing_models:
        print("All eligible common.py models are still offered by OpenRouter.")
        return 0

    for model_name in missing_models:
        print(model_name)

    return 1


if __name__ == "__main__":
    sys.exit(main())

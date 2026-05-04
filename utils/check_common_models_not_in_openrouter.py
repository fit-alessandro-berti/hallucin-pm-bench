import os
import sys
from pathlib import Path

import requests


REPO_ROOT = Path(__file__).resolve().parent.parent
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
sys.path.insert(0, str(REPO_ROOT))

from common import Shared


def _extract_parameter_info(parameters):
    if parameters is None:
        return {"has_api_url": False, "base_model": None}

    if not isinstance(parameters, dict):
        raise RuntimeError(f"Unsupported parameter block: {parameters!r}")

    return {
        "has_api_url": "api_url" in parameters,
        "base_model": parameters.get("base_model"),
    }


def _extract_openrouter_routed_models():
    routed_models = set()

    for item in Shared.MODEL_CATALOGUE:
        if isinstance(item, str):
            model_name = item
            if not model_name[:1].isupper():
                routed_models.add(model_name)
            continue

        if isinstance(item, tuple) and item:
            model_name = item[0]
            parameter_info = _extract_parameter_info(item[1] if len(item) > 1 else None)

            if parameter_info["has_api_url"]:
                continue

            if model_name[:1].isupper():
                continue

            routed_model_name = parameter_info["base_model"] or model_name
            if not routed_model_name[:1].isupper():
                routed_models.add(routed_model_name)
            continue

        raise RuntimeError(f"Unsupported MODEL_CATALOGUE entry: {item!r}")

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

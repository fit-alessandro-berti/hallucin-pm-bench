import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
ANSWERS_DIR = REPO_ROOT / "answers"
sys.path.insert(0, str(REPO_ROOT))

from common import Shared


def _normalized_model_name(model_name):
    return model_name.replace(":", "").replace("/", "")


def _extract_model_catalogue():
    return [
        model if isinstance(model, str) else model[0]
        for model in Shared.MODEL_CATALOGUE
    ]


def _extract_answer_models():
    model_names = set()

    for path in ANSWERS_DIR.iterdir():
        if not path.is_file():
            continue

        model_name, separator, _ = path.name.partition("__")
        if separator:
            model_names.add(model_name)

    return sorted(model_names)


def main():
    common_models = {_normalized_model_name(model_name) for model_name in _extract_model_catalogue()}
    answer_models = _extract_answer_models()
    extra_models = [model_name for model_name in answer_models if model_name not in common_models]

    if not extra_models:
        print("All models in answers/ appear in Shared.MODEL_CATALOGUE.")
        return 0

    for model_name in extra_models:
        print(model_name)

    return 1


if __name__ == "__main__":
    sys.exit(main())

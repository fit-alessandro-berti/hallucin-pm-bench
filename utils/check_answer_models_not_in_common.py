import ast
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
COMMON_PATH = REPO_ROOT / "common.py"
ANSWERS_DIR = REPO_ROOT / "answers"


def _normalized_model_name(model_name):
    return model_name.replace(":", "").replace("/", "")


def _extract_model_catalogue():
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
                    return _extract_model_names(child.value)

    raise RuntimeError("Could not find Shared.MODEL_CATALOGUE in common.py")


def _extract_model_names(node):
    if not isinstance(node, (ast.List, ast.Tuple)):
        raise RuntimeError("Shared.MODEL_CATALOGUE is not a list or tuple literal")

    model_names = []

    for item in node.elts:
        if isinstance(item, ast.Constant) and isinstance(item.value, str):
            model_names.append(item.value)
            continue

        if isinstance(item, ast.Tuple) and item.elts:
            first = item.elts[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                model_names.append(first.value)
                continue

        raise RuntimeError(f"Unsupported MODEL_CATALOGUE entry: {ast.dump(item, include_attributes=False)}")

    return model_names


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

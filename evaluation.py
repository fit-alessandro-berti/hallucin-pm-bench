import os, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from common import *


EVALUATING_MODEL_NAME = "grok-4-1-fast-reasoning"
EVALUATING_API_URL = "https://api.x.ai/v1/"
EVALUATING_API_KEY = os.environ["GROK_API_KEY"]
EVALUATING_PAYLOAD = {}
MAX_THREADS = 100
LEADERBOARD_PATH = "leaderboard.md"

# Hardcoded evaluation-order options. Do not expose these as command-line flags.
PROCESS_ONE_MODEL_AT_A_TIME = True
FILTER_BY_MIN_LEADERBOARD_SCORE = True
MIN_LEADERBOARD_SCORE = 0.0


def _normalized_model_name(model_name):
    return model_name.replace(":", "").replace("/", "")


def _split_markdown_row(line):
    line = line.strip()
    if not line.startswith("|") or not line.endswith("|"):
        return None
    return [cell.strip() for cell in line.strip("|").split("|")]


def _is_markdown_separator(cells):
    return all(cell and set(cell) <= set("-: ") for cell in cells)


def _clean_markdown_value(value):
    return value.replace("*", "").strip()


def _parse_leaderboard(path=LEADERBOARD_PATH):
    if not os.path.exists(path):
        return []

    entries = []
    llm_idx = None
    avg_idx = None

    with open(path, encoding="utf-8") as leaderboard_file:
        for line in leaderboard_file:
            cells = _split_markdown_row(line)
            if not cells:
                continue

            if "LLM" in cells and "AVG" in cells:
                llm_idx = cells.index("LLM")
                avg_idx = cells.index("AVG")
                continue

            if llm_idx is None or _is_markdown_separator(cells):
                continue

            if len(cells) <= max(llm_idx, avg_idx):
                continue

            model_name = _clean_markdown_value(cells[llm_idx])
            try:
                avg = float(_clean_markdown_value(cells[avg_idx]))
            except ValueError:
                continue

            entries.append({"name": model_name, "AVG": avg, "rank": len(entries)})

    entries.sort(key=lambda entry: (-entry["AVG"], entry["rank"]))
    return entries


def _collect_answer_groups(answers_directory="answers", model_filter=None):
    answer_groups = {}

    for answer in sorted(os.listdir(answers_directory)):
        answer_path = os.path.join(answers_directory, answer)
        if not os.path.isfile(answer_path) or os.path.getsize(answer_path) == 0:
            continue

        model_name, separator, _ = answer.partition("__")
        if not separator:
            continue

        if model_filter is not None and model_name != model_filter:
            continue

        answer_groups.setdefault(model_name, []).append(answer)

    return answer_groups


def _find_answer_model_for_leaderboard_model(leaderboard_model, unused_answer_models):
    if leaderboard_model in unused_answer_models:
        return leaderboard_model

    suffix_matches = [model for model in unused_answer_models if model.endswith(leaderboard_model)]
    if not suffix_matches:
        return None

    shortest_extra = min(len(model) - len(leaderboard_model) for model in suffix_matches)
    shortest_matches = [
        model for model in suffix_matches
        if len(model) - len(leaderboard_model) == shortest_extra
    ]

    if len(shortest_matches) == 1:
        return shortest_matches[0]

    print("ambiguous leaderboard model", leaderboard_model, "matches", sorted(shortest_matches))
    return None


def _print_model_list(title, models, scores=None):
    print(title)
    if not models:
        print("  <none>")
        return

    for model in models:
        if scores is not None and model in scores:
            print("  %s (AVG=%.2f)" % (model, scores[model]))
        else:
            print("  %s" % model)


def _evaluation_is_complete(target_directory, answer):
    evaluation_path = os.path.join(target_directory, answer)
    return os.path.exists(evaluation_path) and os.path.getsize(evaluation_path) > 0


def _pending_answers_for_model(model, answer_groups, target_directory):
    return [
        answer for answer in answer_groups.get(model, [])
        if not _evaluation_is_complete(target_directory, answer)
    ]


def _apply_leaderboard_score_filter(leaderboard_models, answer_only_models, scores):
    if not FILTER_BY_MIN_LEADERBOARD_SCORE:
        return leaderboard_models + answer_only_models

    filtered_leaderboard_models = [
        model for model in leaderboard_models
        if scores[model] >= MIN_LEADERBOARD_SCORE
    ]

    if MIN_LEADERBOARD_SCORE <= 0:
        return filtered_leaderboard_models + answer_only_models

    return filtered_leaderboard_models


def _build_evaluation_order(target_directory, model_filter=None):
    answer_groups = _collect_answer_groups(model_filter=model_filter)
    unused_answer_models = set(answer_groups)
    leaderboard_entries = _parse_leaderboard()

    if not leaderboard_entries and not os.path.exists(LEADERBOARD_PATH):
        print(LEADERBOARD_PATH, "not found; all answer models are treated as not in the leaderboard.")

    leaderboard_models = []
    leaderboard_scores = {}
    for entry in leaderboard_entries:
        matched_model = _find_answer_model_for_leaderboard_model(entry["name"], unused_answer_models)
        if matched_model is None:
            continue

        leaderboard_models.append(matched_model)
        leaderboard_scores[matched_model] = entry["AVG"]
        unused_answer_models.remove(matched_model)

    answer_only_models = sorted(unused_answer_models)

    _print_model_list("Models in leaderboard.md, sorted by AVG:", leaderboard_models, leaderboard_scores)
    _print_model_list("Models in answers/ but not in leaderboard.md:", answer_only_models)

    ordered_models = _apply_leaderboard_score_filter(
        leaderboard_models,
        answer_only_models,
        leaderboard_scores
    )
    pending_models = [
        model for model in ordered_models
        if _pending_answers_for_model(model, answer_groups, target_directory)
    ]

    _print_model_list("Final model evaluation order:", pending_models, leaderboard_scores)
    return pending_models, answer_groups


def _evaluate_single_answer(answer, base_model_name, target_directory, include_ground_truth_answer, parameters):
    evaluation_path = os.path.join(target_directory, answer)
    prompt = answer.split("__")[1]
    prompt_content = open(os.path.join("prompts", prompt), encoding="utf-8").read()
    gt_content = open(os.path.join("gt_answers", prompt), encoding="utf-8").read()
    answer_content = open(os.path.join("answers", answer), encoding="utf-8").read().split("</think>")[-1].split("</thought>")[-1]

    evaluation_prompt = []
    evaluation_prompt.append("I ask you to evaluate from 1.0 (minimum) to 10.0 (maximum) the LLM answer provided to the following prompt. Please put the score (from 1.0 to 10.0) in the beginning of your response.")
    if include_ground_truth_answer:
        evaluation_prompt.append("The prompt is accompanied by a ground truth answer, which should be considered to assess the LLM answer. So, the more differences are between the answers and the ground truth answer, the lower is the grade.")
    evaluation_prompt.append("Please evaluate with the utmost strictness. Also small errors should reflect in significant loss of points.")
    evaluation_prompt.append("!! <<PROMPT>>:\n"+prompt_content)
    evaluation_prompt.append("!! <<LLM ANSWER>>:\n"+answer_content)
    if include_ground_truth_answer:
        evaluation_prompt.append("!! <<GROUND TRUTH ANSWER>>:\n"+gt_content)
    evaluation_prompt = "\n\n".join(evaluation_prompt)
    evaluation_prompt = evaluation_prompt + parameters.get("add_prompt", "")

    print("starting", evaluation_path)

    try:
        evaluation = get_response(evaluation_prompt, base_model_name, parameters=parameters)

        if evaluation:
            F = open(evaluation_path, "w", encoding="utf-8")
            F.write(evaluation)
            F.close()

            print("completed", evaluation_path)
            return True
    except Exception as e:
        print("except", evaluation_path, str(e))

    return False


def _evaluate_answer_batch(answers, base_model_name, target_directory, include_ground_truth_answer, parameters):
    modified_something = False
    futures = []

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        for answer in answers:
            futures.append(executor.submit(
                _evaluate_single_answer,
                answer,
                base_model_name,
                target_directory,
                include_ground_truth_answer,
                parameters
            ))

        for future in as_completed(futures):
            try:
                modified_something = future.result() or modified_something
            except Exception as e:
                print("thread except", str(e))

    return modified_something


def evaluate(model_name=EVALUATING_MODEL_NAME, target_directory="evaluations", include_ground_truth_answer=True, filter_self=False, parameters=None):
    if parameters is None:
        parameters = {}
    else:
        parameters = dict(parameters)

    parameters.setdefault(REQUEST_CONTEXT_PARAM, REQUEST_CONTEXT_EVALUATION)
    payload = dict(EVALUATING_PAYLOAD)
    payload.update(parameters.get("payload", {}))
    parameters["payload"] = payload

    if "api_key" not in parameters:
        parameters["api_key"] = EVALUATING_API_KEY

    if "api_url" not in parameters:
        parameters["api_url"] = EVALUATING_API_URL

    os.makedirs(target_directory, exist_ok=True)
    modified_something = False

    m_name = _normalized_model_name(model_name)
    base_model_name = parameters.get("base_model", model_name)

    model_filter = m_name if filter_self else None
    model_order, answer_groups = _build_evaluation_order(target_directory, model_filter=model_filter)

    if PROCESS_ONE_MODEL_AT_A_TIME:
        for model in model_order:
            pending_answers = _pending_answers_for_model(model, answer_groups, target_directory)
            print("processing model", model, "with", len(pending_answers), "pending answers")
            modified_something = _evaluate_answer_batch(
                pending_answers,
                base_model_name,
                target_directory,
                include_ground_truth_answer,
                parameters
            ) or modified_something
    else:
        pending_answers = []
        for model in model_order:
            pending_answers.extend(_pending_answers_for_model(model, answer_groups, target_directory))

        modified_something = _evaluate_answer_batch(
            pending_answers,
            base_model_name,
            target_directory,
            include_ground_truth_answer,
            parameters
        ) or modified_something

    return modified_something


def main1():
    while True:
        modified_something = evaluate()

        print("round finished")

        if not modified_something:
            time.sleep(10)


def main2():
    for model in Shared.MODEL_CATALOGUE:
        parameters = None if isinstance(model, str) else model[1]
        model_name = model if isinstance(model, str) else model[0]

        if model_name in Shared.SELECTED_FOR_SELF_EVALUATION:
            evaluate(model_name, target_directory="stats/self_evaluation", include_ground_truth_answer=False,
                     filter_self=True, parameters=parameters)


if __name__ == "__main__":
    main2()
    main1()

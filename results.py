import math
import os
import re
import time
from statistics import median, pstdev


pattern = r'(?P<sign>[-+]?)(?:(?P<float>\d+\.\d+)|(?P<int>\d+)|(?P<numerator>\d+)/(?P<denominator>\d+))(?!\.)'
reg_expr = re.compile(pattern)

CATEGORY_IDS = tuple(f"{idx:02d}" for idx in range(1, 14))
NAME_PREFIXES = ("anthropic", "x-ai", "openai", "qwen", "mistralai", "mistral", "google", "microsoft", "deepseek", "meta-llama")
OPEN_SOURCE_PATTERNS = ("qwen3", "llama", "mistral", "phi", "glm", "deepseek", "baidu", "moonshot", "oss")
LRM_PATTERNS = ("-think", "gemini-2.5-pro", "thinking", "openaio", "grok-3-mini-beta", "deepseek-r1", "grok-4", "gemini-2.5", "gpt-5", "gpt-oss", "grok-code-fast-1", "qwen3.5", "glm")

MAPPING = {}
MAPPING["C01"] = "C01 Domain-override / Precedence checks"
MAPPING["C02"] = "C02 Event-log fact-extraction"
MAPPING["C03"] = "C03 Text to Model reconstruction"
MAPPING["C04"] = "C04 Compliance / Conformance reasoning"
MAPPING["C05"] = "C05 Counterfactual edits"
MAPPING["C06"] = "C06 Multi-process memory interference"
MAPPING["C07"] = "C07 Change-log diffing"
MAPPING["C08"] = "C08 Temporal / concurrency reasoning"
MAPPING["C09"] = "C09 Unknown-should-remain-unknown"
MAPPING["C10"] = "C10 Domain-synonym enforcement"
MAPPING["C11"] = "C11 Performance analytics commentary"
MAPPING["C12"] = "C12 Misinformation injection"
MAPPING["C13"] = "C13 Edge-case / low-support prompts"

def format_name(llm):
    for p in NAME_PREFIXES:
        if llm.startswith(p):
            return llm[len(p):]

    return llm


def is_open_source(model_name):
    model_name_lower = model_name.lower()

    for p in OPEN_SOURCE_PATTERNS:
        if p in model_name_lower:
            if "mistral-medium" not in model_name_lower and "ministral" not in model_name_lower:
                return ":white_check_mark:"

    return ":x:"


def is_lrm(model_name):
    model_name_lower = model_name.lower()

    for p in LRM_PATTERNS:
        if p in model_name_lower:
            if not ("chat" in model_name_lower or model_name_lower == "gpt-5.1-2025-11-13" or "4.1" in model_name_lower):
                return ":white_check_mark:"

    return ":x:"


def format_numb_in_table(score, max_score, good_diff=0.0):
    score1 = round(score/10.0, 1)
    if score == max_score:
        # :mage_woman:
        return "**%.1f**" % (score1)
    elif score >= max_score - good_diff:
        return "**%.1f**" % (score1)
    return "%.1f" % (score1)


def get_prompts_size():
    size_dict = {}

    with os.scandir("prompts") as entries:
        for entry in entries:
            if not entry.is_file():
                continue

            prompt_name, _ = os.path.splitext(entry.name)
            size_dict[prompt_name] = entry.stat().st_size

    return size_dict


def match_regex(text):
    first_float = None
    first_int = None
    previous_float = None

    for match in reg_expr.finditer(text):
        match_stri = match.group(0)
        number = float(match_stri)
        if number >= 1 and number <= 10:
            if "." in match_stri:
                if first_float is None:
                    first_float = number
                if number == 10.0 and previous_float is not None:
                    return previous_float
                previous_float = number
            elif first_int is None:
                first_int = number

    if first_float is not None:
        return first_float

    return first_int


def _parse_eval_name(file_name):
    stem, _ = os.path.splitext(file_name)
    llm, question = stem.split("__", 1)
    return llm, question


def _load_evaluation_data(evaluation_folder):
    dictio = {}
    per_llm_category_scores = {}
    categories = set()

    with os.scandir(evaluation_folder) as entries:
        for entry in entries:
            if not entry.is_file():
                continue

            llm, question = _parse_eval_name(entry.name)
            category = question[:2]
            categories.add(category)

            with open(entry.path, encoding="utf-8") as evaluation_file:
                number = match_regex(evaluation_file.read())

            if number is None:
                number = 1.0

            dictio.setdefault(llm, {})[question] = number
            llm_category_scores = per_llm_category_scores.setdefault(llm, {})
            llm_category_scores[category] = llm_category_scores.get(category, 0.0) + number

    return dictio, per_llm_category_scores, sorted(categories)


def _format_markdown_value(value):
    if isinstance(value, float):
        if math.isnan(value):
            return "nan"
        text = f"{value:.6f}"
        return text.rstrip("0").rstrip(".")

    return str(value)


def _render_markdown_table(rows, columns=None):
    if not rows:
        return ""

    if columns is None:
        columns = list(rows[0].keys())

    rendered_rows = [[_format_markdown_value(row.get(column, "")) for column in columns] for row in rows]
    widths = []
    for idx, column in enumerate(columns):
        column_width = len(column)
        for row in rendered_rows:
            column_width = max(column_width, len(row[idx]))
        widths.append(column_width)

    header = "| " + " | ".join(column.ljust(widths[idx]) for idx, column in enumerate(columns)) + " |"
    separator = "| " + " | ".join("-" * width for width in widths) + " |"

    body = []
    for row in rendered_rows:
        body.append("| " + " | ".join(row[idx].ljust(widths[idx]) for idx in range(len(columns))) + " |")

    return "\n".join([header, separator] + body)


def _write_markdown_report(path, title, rows, columns=None):
    with open(path, "w", encoding="utf-8") as report_file:
        report_file.write(title)
        report_file.write(_render_markdown_table(rows, columns))


def _safe_mean(values):
    if not values:
        return float("nan")
    return sum(values) / len(values)


def _pearson_correlation(values_x, values_y):
    if not values_x or not values_y or len(values_x) != len(values_y):
        return float("nan")

    mean_x = _safe_mean(values_x)
    mean_y = _safe_mean(values_y)

    numerator = 0.0
    sum_sq_x = 0.0
    sum_sq_y = 0.0
    for value_x, value_y in zip(values_x, values_y):
        centered_x = value_x - mean_x
        centered_y = value_y - mean_y
        numerator += centered_x * centered_y
        sum_sq_x += centered_x * centered_x
        sum_sq_y += centered_y * centered_y

    if sum_sq_x == 0.0 or sum_sq_y == 0.0:
        return float("nan")

    return numerator / math.sqrt(sum_sq_x * sum_sq_y)


def _best_linear_fit(x_values, y_values):
    if not x_values or len(x_values) != len(y_values):
        return float("nan"), float("nan")

    mean_x = _safe_mean(x_values)
    mean_y = _safe_mean(y_values)
    numerator = 0.0
    denominator = 0.0

    for x_value, y_value in zip(x_values, y_values):
        centered_x = x_value - mean_x
        numerator += centered_x * (y_value - mean_y)
        denominator += centered_x * centered_x

    if denominator == 0.0:
        return float("nan"), float("nan")

    slope = numerator / denominator
    intercept = mean_y - slope * mean_x
    return slope, intercept


def get_dictio_results(evaluation_folder):
    dictio, _, _ = _load_evaluation_data(evaluation_folder)
    return dictio


def get_agg_results(evaluation_folder):
    dictio, per_llm_category_scores, categories = _load_evaluation_data(evaluation_folder)
    score_key = "SCORE"
    avg_key = "AVG"
    max_per_cat = {cat: 0.0 for cat in categories}

    for category_scores in per_llm_category_scores.values():
        for category in categories:
            max_per_cat[category] = max(max_per_cat[category], category_scores.get(category, 0.0))

    numeric_results = []
    for llm, scores in dictio.items():
        if any(category not in per_llm_category_scores.get(llm, {}) for category in categories):
            continue

        total_score = sum(scores.values())
        row = {
            "LLM": llm,
            "LRM": is_lrm(llm),
            "OS": is_open_source(llm),
            avg_key: round(total_score / 39.0, 2),
            score_key: total_score,
        }

        category_scores = per_llm_category_scores[llm]
        for category in categories:
            row["C" + category] = category_scores[category]

        numeric_results.append(row)

    numeric_results.sort(key=lambda row: (row[score_key], row["LLM"]), reverse=True)

    display_results = []
    for row in numeric_results:
        display_row = {"LLM": format_name(row["LLM"]), "LRM": row["LRM"], "OS": row["OS"], avg_key: row[avg_key]}
        for category in categories:
            display_row["C" + category] = format_numb_in_table(row["C" + category], max_per_cat[category])
        display_results.append(display_row)

    return display_results, dictio, numeric_results


def measure_inter_category_correlation(results):
    vectors = []
    for category in CATEGORY_IDS:
        key = "C" + category
        vectors.append([row[key] for row in results])

    table = []
    for idx0, category0 in enumerate(CATEGORY_IDS):
        table_row = {"Category": MAPPING["C" + category0]}
        for idx1, category1 in enumerate(CATEGORY_IDS):
            table_row["C" + category1] = _pearson_correlation(vectors[idx0], vectors[idx1])
        table.append(table_row)

    columns = ["Category"] + ["C" + category for category in CATEGORY_IDS]
    _write_markdown_report("stats/inter_correlation.md", "# Inter-Features Correlation\n\n", table, columns)


def get_vectors(dictio, get_std=True):
    vectors = [[] for _ in CATEGORY_IDS]
    for scores in dictio.values():
        grouped_scores = {}
        for question, score in scores.items():
            grouped_scores.setdefault(question[:2], []).append(score)

        for idx, category in enumerate(CATEGORY_IDS):
            category_scores = grouped_scores.get(category)
            if category_scores and len(category_scores) == 3:
                if get_std:
                    vectors[idx].append(pstdev(category_scores))
                else:
                    vectors[idx].append(_safe_mean(category_scores))
    return vectors


def measure_intra_variation(dictio):
    vectors = get_vectors(dictio)

    intra_variation = [median(values) if values else float("nan") for values in vectors]
    table = []

    for idx, category in enumerate(CATEGORY_IDS):
        table.append({"Category": MAPPING["C" + category], "Median of Std": intra_variation[idx]})

    _write_markdown_report("stats/intra_variation.md", "# Intra-Category Variation\n\n", table)


def get_best_linear_fit(prompts_size, dictio):
    X = []
    Y = []

    for llm in dictio:
        for key, value in dictio[llm].items():
            Y.append(value)
            X.append(prompts_size[key])

    m, b = _best_linear_fit(X, Y)

    with open("stats/best_linear_fit.md", "w", encoding="utf-8") as fit_file:
        fit_file.write("m=%.5f\nb=%.5f\n" % (m, b))


def compute_avg_std_per_category(dictio):
    vectors = get_vectors(dictio, get_std=False)

    table = []
    for idx, category in enumerate(CATEGORY_IDS):
        scaled_values = [value * 0.3 for value in vectors[idx]]
        table.append({"Category": MAPPING["C" + category], "Avg": _safe_mean(scaled_values), "Std": pstdev(scaled_values) if scaled_values else float("nan")})

    _write_markdown_report("stats/avg_std_category.md", "# Average/Std per Category\n\n", table)


def main(evaluation_folder, target_leaderboard, write_extra_stats=True):
    results, dictio, numeric_results = get_agg_results(evaluation_folder)
    if write_extra_stats:
        measure_inter_category_correlation(numeric_results)
        measure_intra_variation(dictio)
        compute_avg_std_per_category(dictio)
        prompts_size = get_prompts_size()
        get_best_linear_fit(prompts_size, dictio)

    columns = list(results[0].keys()) if results else ["LLM", "LRM", "OS", "AVG"] + ["C" + category for category in CATEGORY_IDS]
    with open(target_leaderboard, "w", encoding="utf-8") as leaderboard_file:
        leaderboard_file.write("## Overall Leaderboard (grok-4.2 used as the Judge)\n\n")
        leaderboard_file.write("The higher the score, the better the model.\nMaximum attainable score per category: **3 points**.\nThe average **/10.0** is computed over all the scores.\n\n")
        leaderboard_file.write(_render_markdown_table(results, columns))



if __name__ == "__main__":
    t0 = time.time_ns()
    main("stats/self_evaluation", "stats/self_evaluation.md", write_extra_stats=False)
    main("evaluations", "leaderboard.md", write_extra_stats=True)
    t1 = time.time_ns()
    print((t1 - t0) / 10**9)

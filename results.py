import os
import re
import numpy as np
import pandas as pd


pattern = r'(?P<sign>[-+]?)(?:(?P<float>\d+\.\d+)|(?P<int>\d+)|(?P<numerator>\d+)/(?P<denominator>\d+))(?!\.)'
reg_expr = re.compile(pattern)

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
    patterns = ["anthropic", "x-ai", "openai", "qwen"]

    for p in patterns:
        if llm.startswith(p):
            return llm[len(p):]

    return llm


def is_open_source(model_name):
    patterns = {"qwen3", "llama", "mistral"}

    for p in patterns:
        if p.lower() in model_name.lower():
            if not "medium" in model_name.lower():
                return ":white_check_mark:"

    return ":x:"


def is_lrm(model_name):
    patterns = {"-think", "gemini-2.5-pro", "thinking", "openaio", "grok-3-mini-beta"}

    for p in patterns:
        if p.lower() in model_name.lower():
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

    for prompt in os.listdir("prompts"):
        size_dict[prompt.split(".")[0]] = os.path.getsize(os.path.join("prompts", prompt))

    return size_dict


def match_regex(text):
    matches = list(reg_expr.finditer(text))
    matches_numbers_floats = []
    matches_numbers_ints = []
    for match in matches:
        match_stri = str(match.group(0))
        number = float(match_stri)
        if number >= 1 and number <= 10:
            if "." in match_stri:
                matches_numbers_floats.append(number)
            else:
                matches_numbers_ints.append(number)

    if matches_numbers_floats:
        if 10.0 in matches_numbers_floats:
            idx = matches_numbers_floats.index(10.0)
            if idx > 0:
                return matches_numbers_floats[idx-1]
        return matches_numbers_floats[0]
    elif matches_numbers_ints:
        return matches_numbers_ints[0]


def get_dictio_results(evaluation_folder):
    evaluations = os.listdir(evaluation_folder)

    dictio = {}

    for ev in evaluations:
        ev_content = open(os.path.join(evaluation_folder, ev), encoding="utf-8").read()

        llm = ev.split("__")[0]
        question = ev.split("__")[1].split(".")[0]

        if not llm in dictio:
            dictio[llm] = {}

        number = match_regex(ev_content)
        if number is None:
            number = 1.0

        dictio[llm][question] = number

    return dictio


def get_agg_results(evaluation_folder):
    categories = os.listdir(evaluation_folder)
    categories = set(x.split("__")[1].split("_")[0] for x in categories)
    categories = sorted(list(categories))

    dictio = get_dictio_results(evaluation_folder)
    score_key = "SCORE"
    avg_key = "AVG"

    max_per_cat = {}

    results = []
    for llm in dictio:
        summ = sum(dictio[llm].values())
        row = {"LLM": llm, "LRM": is_lrm(llm), "OS": is_open_source(llm), avg_key: 0.0, score_key: summ}

        for cat in categories:
            if cat not in max_per_cat:
                max_per_cat[cat] = 0.0

            this_summ = sum(dictio[llm][x] for x in dictio[llm] if x.startswith(cat))
            max_per_cat[cat] = max(max_per_cat[cat], this_summ)

            if this_summ > 0:
                row["C"+cat] = this_summ

        results.append(row)

    results.sort(key=lambda x: (x[score_key], x["LLM"]), reverse=True)

    for i in range(1, 14):
        cat_name = "C" + str(i).zfill(2)
        j = 0
        while j < len(results):
            if cat_name not in results[j]:
                del results[j]
                continue

            results[j][cat_name] = format_numb_in_table(results[j][cat_name], max_per_cat[cat_name[1:]])
            j = j + 1

    for j in range(len(results)):
        results[j][avg_key] = round(results[j][score_key] / 39.0, 2)
        results[j][score_key] = round(results[j][score_key]/10.0, 1)
        results[j]["LLM"] = format_name(results[j]["LLM"])
        del results[j][score_key]

    return results, dictio


def measure_inter_category_correlation(results):
    from scipy.stats import pearsonr

    vectors = []
    for cat0 in range(1, 14):
        cat = "C"+str(cat0).zfill(2)
        vectors.append([])

        for row in results:
            vectors[-1].append(float(row[cat].replace("**", "")))

    table = []

    for cat0 in range(1, 14):
        table.append({"Category": MAPPING["C"+str(cat0).zfill(2)]})
        for cat1 in range(1, 14):
            table[-1]["C"+str(cat1).zfill(2)] = pearsonr(vectors[cat0-1], vectors[cat1-1]).statistic

    table = pd.DataFrame(table)
    table_md = table.to_markdown(index=False)

    F = open("stats/inter_correlation.md", "w")
    F.write("# Inter-Features Correlation\n\n")
    F.write(table_md)
    F.close()


def measure_intra_variation(dictio):
    vectors = [[] for i in range(1, 14)]
    for llm, scores in dictio.items():
        for i in range(1, 14):
            pref = str(i).zfill(2)
            catscor = [y for x, y in scores.items() if x.startswith(pref)]
            if len(catscor) == 3:
                vectors[i-1].append(np.std(catscor))
    intra_variation = [np.median(vectors[i]) for i in range(len(vectors))]
    table = []

    for i in range(1, 14):
        cat = "C"+str(i).zfill(2)

        table.append({"Category": MAPPING[cat], "Median of Std": intra_variation[i-1]})

    table = pd.DataFrame(table)
    table_md = table.to_markdown(index=False)

    F = open("stats/intra_variation.md", "w")
    F.write("# Intra-Category Variation\n\n")
    F.write(table_md)
    F.close()


def get_best_linear_fit(prompts_size, dictio):
    X = []
    Y = []

    for llm in dictio:
        for key, value in dictio[llm].items():
            Y.append(value)
            X.append(prompts_size[key])

    m, b = np.polyfit(X, Y, 1)

    F = open("stats/best_linear_fit.md", "w", encoding="utf-8")
    F.write("m=%.5f\nb=%.5f\n" % (m ,b))
    F.close()


def main(evaluation_folder, target_leaderboard, write_extra_stats=True):
    results, dictio = get_agg_results(evaluation_folder)
    if write_extra_stats:
        measure_inter_category_correlation(results)
        measure_intra_variation(dictio)
        prompts_size = get_prompts_size()
        get_best_linear_fit(prompts_size, dictio)

    results = pd.DataFrame(results)

    res = results.to_markdown(index=False)

    F = open(target_leaderboard, "w")

    F.write("## Overall Leaderboard (gpt-4.1 used as the Judge)\n\n")
    F.write("The higher the score, the better the model.\nMaximum attainable score per category: **3 points**.\nThe average **/10.0** is computed over all the scores.\n\n")
    F.write(res)

    F.close()



if __name__ == "__main__":
    main("stats/self_evaluation", "stats/self_evaluation.md", write_extra_stats=False)
    main("evaluations", "leaderboard.md", write_extra_stats=True)

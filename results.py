import os
import re
import pandas as pd


pattern = r'(?P<sign>[-+]?)(?:(?P<float>\d+\.\d+)|(?P<int>\d+)|(?P<numerator>\d+)/(?P<denominator>\d+))(?!\.)'
reg_expr = re.compile(pattern)


def is_open_source(model_name):
    patterns = {"qwen3", "llama"}

    for p in patterns:
        if p.lower() in model_name.lower():
            return ":white_check_mark:"

    return ":x:"


def is_lrm(model_name):
    patterns = {"-think", "gemini-2.5"}

    for p in patterns:
        if p.lower() in model_name.lower():
            return ":white_check_mark:"

    return ":x:"


def format_numb_in_table(score, max_score, good_diff=0.1):
    score1 = round(score/10.0, 1)
    if score == max_score:
        return ":mage_woman: **%.1f**" % (score1)
    elif score >= max_score - good_diff:
        return "**%.1f**" % (score1)
    return "%.1f" % (score1)


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


def get_dictio_results():
    evaluations = os.listdir("evaluations")

    dictio = {}

    for ev in evaluations:
        ev_content = open(os.path.join("evaluations", ev), encoding="utf-8").read()

        llm = ev.split("__")[0]
        question = ev.split("__")[1].split(".")[0]

        if not llm in dictio:
            dictio[llm] = {}

        number = match_regex(ev_content)
        if number is None:
            number = 1.0

        dictio[llm][question] = number

    return dictio


def get_agg_results():
    categories = os.listdir("evaluations")
    categories = set(x.split("__")[1].split("_")[0] for x in categories)
    categories = sorted(list(categories))

    dictio = get_dictio_results()
    score_key = "SCORE"
    max_per_cat = {}

    results = []
    for llm in dictio:
        summ = sum(dictio[llm].values())
        row = {"LLM": llm, "LRM?": is_lrm(llm), "OS?": is_open_source(llm), score_key: summ}

        for cat in categories:
            if cat not in max_per_cat:
                max_per_cat[cat] = 0.0

            this_summ = sum(dictio[llm][x] for x in dictio[llm] if x.startswith(cat))
            max_per_cat[cat] = max(max_per_cat[cat], this_summ)

            row["C"+cat] = this_summ

        results.append(row)

    results.sort(key=lambda x: (x[score_key], x["LLM"]), reverse=True)

    for i in range(1, 13):
        cat_name = "C" + str(i).zfill(2)
        for j in range(len(results)):
            if cat_name not in results[j]:
                results[j][cat_name] = format_numb_in_table(0.0, max_per_cat[cat_name[1:]])
            else:
                results[j][cat_name] = format_numb_in_table(results[j][cat_name], max_per_cat[cat_name[1:]])

    for j in range(len(results)):
        results[j][score_key] = round(results[j][score_key]/10.0, 1)

    return results, dictio



if __name__ == "__main__":
    results, dictio = get_agg_results()
    results = pd.DataFrame(results)

    res = results.to_markdown(index=False)

    F = open("leaderboard.md", "w")

    F.write("## Overall Leaderboard (gpt-4.1 used as the Judge)\n\n")
    F.write("The higher the score, the better the model. Maximum attainable score: **39 points**\n\n")
    F.write(res)

    F.close()

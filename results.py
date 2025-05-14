import os
import re
import pandas as pd


pattern = r'(?P<sign>[-+]?)(?:(?P<float>\d+\.\d+)|(?P<int>\d+)|(?P<numerator>\d+)/(?P<denominator>\d+))(?!\.)'
reg_expr = re.compile(pattern)


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

    results = []
    for llm in dictio:
        summ = sum(dictio[llm].values())
        row = {"LLM": llm, "TOTAL SCORE": round(summ/10.0, 1)}

        for cat in categories:
            this_summ = sum(dictio[llm][x] for x in dictio[llm] if x.startswith(cat))
            row["C"+cat] = round(this_summ/10.0, 1)

        results.append(row)

    results.sort(key=lambda x: (x["TOTAL SCORE"], x["LLM"]), reverse=True)
    print(results)

    return results, dictio



if __name__ == "__main__":
    results, dictio = get_agg_results()
    results = pd.DataFrame(results)

    results.to_markdown("leaderboard.md", index=False)

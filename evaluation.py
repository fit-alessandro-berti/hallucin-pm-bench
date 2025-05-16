import os, time
from common import *


EVALUATING_MODEL_NAME = "openai/gpt-4.1"


def evaluate(model_name=EVALUATING_MODEL_NAME, target_directory="evaluations", include_ground_truth_answer=True, filter_self=False, parameters=None):
    if parameters is None:
        parameters = {}

    modified_something = False

    m_name = model_name.replace(":", "").replace("/", "")
    base_model_name = parameters.get("base_model", model_name)

    for answer in os.listdir("answers"):
        if filter_self:
            if not answer.startswith(m_name+"__"):
                continue

        evaluation_path = os.path.join(target_directory, answer)

        if (not os.path.exists(evaluation_path)) or (os.path.getsize(evaluation_path) == 0):
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
                    modified_something = True
            except Exception as e:
                print("except", evaluation_path, str(e))

    return modified_something


def main1():
    while True:
        modified_something = evaluate()

        if not modified_something:
            pass
            #break

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

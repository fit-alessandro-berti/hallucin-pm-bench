import os
from common import *


EVALUATING_MODEL_NAME = "openai/gpt-4.1-mini"


def evaluate():
    model_name = EVALUATING_MODEL_NAME
    m_name = model_name.replace(":", "").replace("/", "")

    for answer in os.listdir("answers"):
        evaluation_path = os.path.join("evaluations", answer)

        if (not os.path.exists(evaluation_path)) or (os.path.getsize(evaluation_path) == 0):
            prompt = answer.split("__")[1]
            prompt_content = open(os.path.join("prompts", prompt), encoding="utf-8").read()
            gt_content = open(os.path.join("gt_answers", prompt), encoding="utf-8").read()
            answer_content = open(os.path.join("answers", answer), encoding="utf-8").read()

            evaluation_prompt = []
            evaluation_prompt.append("I ask you to evaluate from 1.0 (minimum) to 10.0 (maximum) the LLM answer provided to the following prompt.")
            evaluation_prompt.append("The prompt is accompanied by a ground truth answer, which should be considered to assess the LLM answer. So, the more differences are between the answers and the ground truth answer, the lower is the grade.")
            evaluation_prompt.append("Please evaluate with the utmost strictness. Also small errors should reflect in significant loss of points.")
            evaluation_prompt.append("!! <<PROMPT>>:\n"+prompt_content)
            evaluation_prompt.append("!! <<LLM ANSWER>>:\n"+answer_content)
            evaluation_prompt.append("!! <<GROUND TRUTH ANSWER>>:\n"+gt_content)
            evaluation_prompt = "\n\n".join(evaluation_prompt)

            print("starting", evaluation_path)

            try:
                evaluation = get_response(evaluation_prompt, model_name)

                if evaluation:
                    F = open(evaluation_path, "w", encoding="utf-8")
                    F.write(evaluation)
                    F.close()

                    print("completed", evaluation_path)
            except Exception as e:
                print("except", evaluation_path, str(e))


if __name__ == "__main__":
    evaluate()

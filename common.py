import os
from pathlib import Path

import requests
import traceback
import json


REQUEST_CONTEXT_PARAM = "request_context"
REQUEST_CONTEXT_ANSWER = "answer"
REQUEST_CONTEXT_EVALUATION = "evaluation"
REQUEST_CONTEXT_UNKNOWN = "unknown"
API_KEY_ENV_PARAM = "api_key_env"

EVALUATIONS_DIR = "evaluations-grok43"
MODELS_CONFIG_PATH = Path(__file__).with_name("models.json")


def _load_models_config(path=MODELS_CONFIG_PATH):
    with path.open(encoding="utf-8") as config_file:
        return json.load(config_file)


def _normalize_model_catalogue_entry(entry):
    if isinstance(entry, str):
        return entry

    if (
        isinstance(entry, list)
        and len(entry) == 2
        and isinstance(entry[0], str)
        and isinstance(entry[1], dict)
    ):
        return (entry[0], entry[1])

    raise ValueError(f"Unsupported model catalogue entry in {MODELS_CONFIG_PATH}: {entry!r}")


def _load_model_catalogue():
    config = _load_models_config()
    model_catalogue = config.get("model_catalogue")

    if not isinstance(model_catalogue, list):
        raise ValueError(f"{MODELS_CONFIG_PATH} must contain a model_catalogue list")

    return [_normalize_model_catalogue_entry(entry) for entry in model_catalogue]


def _uses_responses_api(api_url):
    return "api.x.ai" in api_url


def _build_api_url(api_url, endpoint):
    return api_url.rstrip("/") + "/" + endpoint.lstrip("/")


def _build_payload(prompt, model_name, parameters, use_responses_api):
    payload = dict(parameters.get("payload", {}))

    if use_responses_api and "reasoning_effort" in payload and "reasoning" not in payload:
        payload["reasoning"] = {"effort": payload.pop("reasoning_effort")}

    if use_responses_api:
        payload.update({
            "model": model_name,
            "input": prompt,
        })
    else:
        payload.update({
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
        })

    return payload


def _extract_responses_reasoning(resp_json):
    reasoning_parts = []

    for item in resp_json.get("output", []):
        if item.get("type") != "reasoning":
            continue

        for summary_item in item.get("summary", []):
            if isinstance(summary_item, dict) and summary_item.get("text"):
                reasoning_parts.append(summary_item["text"])

    return "\n".join(reasoning_parts).strip()


def _extract_responses_message(resp_json):
    if resp_json.get("output_text"):
        return resp_json["output_text"]

    message_parts = []

    for item in resp_json.get("output", []):
        if item.get("type") != "message":
            continue

        for content_item in item.get("content", []):
            if not isinstance(content_item, dict):
                continue

            if content_item.get("type") in {"output_text", "text"} and content_item.get("text"):
                message_parts.append(content_item["text"])

    return "\n".join(message_parts).strip()


def _extract_text_value(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(filter(None, (_extract_text_value(item) for item in value))).strip()
    if isinstance(value, dict):
        parts = []
        for key in ("text", "content", "output_text", "reasoning", "thinking", "reasoning_content"):
            text = _extract_text_value(value.get(key))
            if text:
                parts.append(text)
        return "\n".join(parts).strip()
    return str(value)


def _extract_chat_message_parts(message):
    content = message.get("content", "")
    if isinstance(content, str):
        return content, _extract_text_value(message.get("reasoning_content"))

    if not isinstance(content, list):
        return _extract_text_value(content), _extract_text_value(message.get("reasoning_content"))

    message_parts = []
    reasoning_parts = []

    for item in content:
        if isinstance(item, dict):
            item_type = item.get("type", "")
            is_reasoning = item_type in {"reasoning", "thinking", "reasoning_content"}

            for key in ("text", "content", "output_text"):
                text = _extract_text_value(item.get(key))
                if text:
                    if is_reasoning:
                        reasoning_parts.append(text)
                    else:
                        message_parts.append(text)

            for key in ("reasoning", "thinking", "reasoning_content"):
                text = _extract_text_value(item.get(key))
                if text:
                    reasoning_parts.append(text)
        else:
            text = _extract_text_value(item)
            if text:
                message_parts.append(text)

    top_level_reasoning = _extract_text_value(message.get("reasoning_content"))
    if top_level_reasoning:
        reasoning_parts.append(top_level_reasoning)

    return "\n".join(message_parts).strip(), "\n".join(reasoning_parts).strip()


def _final_response_only(response_message, reasoning_content):
    return response_message


def _parse_response_json(resp_json, use_responses_api):
    if use_responses_api:
        response_message = _extract_responses_message(resp_json)
        reasoning_content = _extract_responses_reasoning(resp_json)

        return _final_response_only(response_message, reasoning_content)

    if "choices" not in resp_json:
        print(resp_json)

    message = resp_json["choices"][-1]["message"]

    response_message, reasoning_content = _extract_chat_message_parts(message)
    return _final_response_only(response_message, reasoning_content)



class Shared:
    MODEL_CATALOGUE = _load_model_catalogue()

    SELECTED_FOR_SELF_EVALUATION = ["mistralai/ministral-3b",
                                    "mistral/ministral-8b",
                                    "gpt-4.1-nano",
                                    "qwen/qwen3-30b-a3b-nothink",
                                    "qwen/qwen3-14b-nothink",
                                    "meta-llama/llama-4-scout",
                                    "google/gemini-2.0-flash-lite-001",
                                    "google/gemini-2.0-flash-001",
                                    "google/gemini-2.5-flash-preview"]


def get_response(prompt, model_name, parameters=None):
    if parameters is None:
        parameters = {}

    request_context = parameters.get(REQUEST_CONTEXT_PARAM, REQUEST_CONTEXT_UNKNOWN)
    api_url = parameters["api_url"] if "api_url" in parameters else "https://openrouter.ai/api/v1/"
    if "api_key" in parameters:
        api_key = parameters["api_key"]
    elif API_KEY_ENV_PARAM in parameters:
        api_key = os.environ[parameters[API_KEY_ENV_PARAM]]
    else:
        api_key = os.environ["OPENROUTER_API_KEY"]
    use_responses_api = _uses_responses_api(api_url)

    complete_url = _build_api_url(api_url, "responses" if use_responses_api else "chat/completions")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = _build_payload(prompt, model_name, parameters, use_responses_api)

    enable_streaming = False

    if enable_streaming:
        payload["stream"] = True
        response_message = ""
        thinking_content = ""

        chunk_count = 0

        with requests.post(complete_url, headers=headers, json=payload, stream=True, timeout=20*60) as resp:
            if not resp.status_code == 200:
                print(request_context, resp.status_code)

            for line in resp.iter_lines():
                if not line:
                    continue
                decoded_line = line.decode("utf-8")

                # OpenAI-style streaming lines begin with "data: "
                if decoded_line.startswith("data: "):
                    data_str = decoded_line[len("data: "):].strip()
                    if data_str == "[DONE]":
                        # End of stream
                        break
                    try:
                        data_json = json.loads(data_str)
                        if use_responses_api:
                            if data_json.get("type") == "response.output_text.delta":
                                chunk_content = data_json.get("delta", "")
                                if chunk_content:
                                    response_message += chunk_content
                                    chunk_count += 1
                            elif data_json.get("type") == "response.reasoning_summary_text.delta":
                                chunk_reasoning_content = data_json.get("delta", "")
                                if chunk_reasoning_content:
                                    thinking_content += chunk_reasoning_content
                                    chunk_count += 1
                        elif "choices" in data_json:
                            # Each chunk has a delta with partial content
                            chunk_content = data_json["choices"][0]["delta"].get("content", "")
                            chunk_reasoning_content = data_json["choices"][0]["delta"].get("reasoning_content", "")

                            if chunk_content:
                                response_message += chunk_content
                                chunk_count += 1
                                # print(chunk_count)
                                if chunk_count % 10 == 0:
                                    # print(chunk_count, len(response_message), response_message.replace("\n", " ").replace("\r", "").strip())
                                    pass
                            elif chunk_reasoning_content:
                                thinking_content += chunk_reasoning_content
                                chunk_count += 1
                                # print("thinking", chunk_count)
                                if chunk_count % 10 == 0:
                                    # print("thinking", chunk_count, len(response_message), response_message.replace("\n", " ").replace("\r", "").strip())
                                    pass
                    except json.JSONDecodeError:
                        # Possibly a keep-alive or incomplete chunk
                        traceback.print_exc()

    else:
        with requests.post(complete_url, headers=headers, json=payload, timeout=20*60) as resp:
            if not resp.status_code == 200:
                print(request_context, resp.status_code)
                print(resp.text)

            resp_json = resp.json()
            response_message = _parse_response_json(resp_json, use_responses_api)

    return response_message


if __name__ == "__main__":
    print(get_response("How many R are in Strawberry?", "openai/gpt-4.1-mini"))

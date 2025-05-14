import requests
import traceback
import json


class Shared:
    API_URL = "https://openrouter.ai/api/v1/"
    API_KEY = open("api_key.txt", "r").read().strip()


def get_response(prompt, model_name):
    complete_url = Shared.API_URL + "chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {Shared.API_KEY}"
    }

    messages = [{"role": "user", "content": prompt}]
    payload = {
        "model": model_name,
        "messages": messages,
    }

    payload["stream"] = True
    response_message = ""
    thinking_content = ""

    chunk_count = 0

    with requests.post(complete_url, headers=headers, json=payload, stream=True) as resp:
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
                    if "choices" in data_json:
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

    if thinking_content:
        response_message = ["<think>", thinking_content, "</think>", response_message]
        response_message = "\n".join(response_message)

    return response_message


if __name__ == "__main__":
    print(get_response("How many R are in Strawberry?", "openai/gpt-4.1-mini"))

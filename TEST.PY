# test_gemini.py
# Simple test for a Gemini API key using the Generative Language REST API.
# Requires: requests (install with `pip install requests`)


import os
import requests
import json


def main():
    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")


    if not api_key:
        print("❌ Please set your GEMINI_API_KEY environment variable first.")
        return


    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }


    data = {
        "contents": [
            {"parts": [{"text": "Say a short friendly hello and identify the model."}]}
        ]
    }


    print(f"➡️ Sending request to {url} ...")


    response = requests.post(url, headers=headers, data=json.dumps(data))


    print(f"HTTP status: {response.status_code}")
    if response.ok:
        print("✅ Response JSON:")
        print(json.dumps(response.json(), indent=2))
    else:
        print("❌ Request failed:")
        print(response.text)


if __name__ == "__main__":
    main()

import base64
import requests
import json

from fastapi import HTTPException

import logging

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = "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"

def analyze_garbage_image(image_path: str):
    image_encoded_string = ""

    try:
        with open(image_path, "rb") as file:
            image_encoded_string = base64.b64encode(file.read()).decode("utf-8")
    except:
        raise HTTPException(status_code=500, detail="Failed to read image for AI analysis")

    image_data_url = f"data:image/jpeg;base64;{image_encoded_string}"

    prompt = (
        "You are an AI city triage inspector. Comprehensively and concisely analyze the provided image of uncollected garbage."
        "Your output should only contain the analysis and nothing else. Also, limit your output to 5 sentences max."
        "If the provided image is not an image of uncollected garbage, state that in your output and terminate the analysis immediately."
    )

    payload = {
        "model": "nex-agi/nex-n2-pro:free",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "imageUrl": {
                            "url": image_data_url
                        }
                    }
                ]
            }
        ]
    }

    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        data=json.dumps(payload)
    )

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"OpenRouter gateway error: {response.text}")

    result = response.json()
    logger.info(f"OpenRouter response: {result}")
    ai_summary = result["choices"][0]["message"]["content"]

    return ai_summary
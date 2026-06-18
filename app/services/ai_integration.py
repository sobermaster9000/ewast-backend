import base64
import requests
import json

from fastapi import HTTPException

from sqlmodel import Session

from app.schemas import ReportType, Report
from app.services.database import db_engine

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = "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"

def analyze_garbage_report(report_type: ReportType, report_notes: str | None = None, report_image_url: str | None = None) -> str:
    if report_notes is None and report_image_url is None:
        raise Exception("No report notes or image to proceed with analysis")

    image_data_url = ""
    image_encoded_string = ""

    if report_image_url:
        try:
            with open(report_image_url, "rb") as file:
                image_encoded_string = base64.b64encode(file.read()).decode("utf-8")
        except:
            # raise HTTPException(status_code=500, detail="Failed to read image for AI analysis")
            raise Exception(f"Failed to read image {report_image_url} for AI analysis")

        image_data_url = f"data:image/jpeg;base64;{image_encoded_string}"

    ### prompt structure ###
    # general instructions
    # report_notes additive
    # report_image additive

    prompt = (
        "You are a professional city triage inspector. You are to comprehensively and concisely analyze a provided report of uncollected garbage. "
        f"The report has a report type of {report_type.value}. "
        "Your output should only contain the analysis and nothing else. Also, limit your output to 5 sentences max. "
    )

    payload = {
        "model": "nex-agi/nex-n2-pro:free",
        "messages": [
            {
                "role": "user",
                "content": []
            }
        ]
    }

    if report_notes:
        prompt += (
            "You will be given some notes on the report, which was annotated by a citizen. You may use these notes to further supplement your analysis. "
            "Here are the report notes, make sure to translate any Tagalog, Bisaya, or any other Filipino dialect to English first before parsing the full notes:"
            f"{report_notes}"
        )

    payload["messages"][0]["content"].append({
        "type": "text",
        "text": prompt
    })

    if image_data_url:
        prompt += (
            "You will also be given an image of uncollected garbage that is associated with the report. You may also use this image to further supplement your analysis. "
            "If the provided image is not an image of uncollected garbage, state that in your output."
        )

        payload["messages"][0]["content"][0]["text"] = prompt
        payload["messages"][0]["content"].append({
            "type": "image_url",
            "imageUrl": {
                "url": image_data_url
            }
        })

    # payload = {
    #     "model": "nex-agi/nex-n2-pro:free",
    #     "messages": [
    #         {
    #             "role": "user",
    #             "content": [
    #                 {
    #                     "type": "text",
    #                     "text": prompt
    #                 },
    #                 {
    #                     "type": "image_url",
    #                     "imageUrl": {
    #                         "url": image_data_url
    #                     }
    #                 }
    #             ]
    #         }
    #     ]
    # }

    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        data=json.dumps(payload)
    )

    if response.status_code != 200:
        # raise HTTPException(status_code=502, detail=f"OpenRouter gateway error: {response.text}")
        raise Exception(f"OpenRouter gateway error: {response.text}")

    result = response.json()
    # logger.info(f"OpenRouter response: {result}")
    ai_summary = result["choices"][0]["message"]["content"]

    return ai_summary

def process_ai_report_analysis(report_id: int) -> None:
    with Session(db_engine) as session:
        report = session.get(Report, report_id)
        if not report:
            return
        try:
            ai_summary = analyze_garbage_report(report.type, report.notes, report.image_url)
            report.ai_summary = ai_summary
            session.add(report)
            session.commit()
        except Exception as error:
            logger.fatal(f"An error occured while processing the AI report analysis: {error}")
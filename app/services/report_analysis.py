import base64
import requests
import json
import os

from fastapi import HTTPException

from sqlmodel import Session, select

from app.schemas import ReportType, Report, Barangay, Summary
from app.services.database import db_engine
from app.config import settings

from shapely.geometry import Point, Polygon

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

def get_barangay_report_analysis(barangay_id: int) -> str:
    with Session(db_engine) as session:
        barangay = session.get(Barangay, barangay_id)
        if not barangay:
            raise Exception("Barangay not found")
        return barangay.ai_summary if barangay.ai_summary else ""

def get_general_report_analysis() -> str:
    with Session(db_engine) as session:
        summary = session.exec(select(Summary)).first()
        if not summary:
            summary = Summary()
            session.add(summary)
            session.commit()
            session.refresh(summary)
        return summary.general_summary if summary.general_summary else ""

def get_barangay_id_of_report(report: Report) -> int:
    report_point = Point(report.longitude, report.latitude)
    with Session(db_engine) as session:
        barangays = session.exec(select(Barangay)).all()
        for barangay in barangays:
            if len(barangay.bounds_coords) < 3:
                continue
            polygon_coords = [(long, lat) for lat, long in barangay.bounds_coords]
            barangay_polygon = Polygon(polygon_coords)
            if barangay_polygon.contains(report_point) and barangay.barangay_id:
                return barangay.barangay_id
    return 0

def analyze_garbage_report(report: Report) -> dict[str, str | int]:
    report_type = report.type
    report_notes = report.notes
    report_image_url = report.image_url

    if report_notes is None and report_image_url is None:
        raise Exception("No report notes or image to proceed with analysis")

    image_data_url = ""
    image_encoded_string = ""

    if report_image_url:
        try:
            with open(report_image_url, "rb") as file:
                image_encoded_string = base64.b64encode(file.read()).decode("utf-8")
            file_extension = os.path.splitext(report_image_url)[1][1:]
            image_data_url = f"data:image/{file_extension};base64,{image_encoded_string}"
            logger.info(f"Image encoded into url with .{file_extension} file extension and {len(image_encoded_string)} characters encoded")
        except:
            # raise HTTPException(status_code=500, detail="Failed to read image for AI analysis")
            raise Exception(f"Failed to read image {report_image_url} for AI analysis")

    if not report_notes:
        report_notes = ""

    barangay_id = get_barangay_id_of_report(report)

    barangay_analysis = ""
    try:
        barangay_analysis = get_barangay_report_analysis(barangay_id)
    except Exception as error:
        logger.warning(f"Could not retrieve barangay analysis of barangay with id {barangay_id}\nError: {error}")

    overall_analysis = ""
    try:
        overall_analysis = get_general_report_analysis()
    except Exception as error:
        logger.warning(f"Could not retrieve overall reports analysis\nError: {error}")

    prompt = f"""\
You are an expert municipal data analyst and city triage inspector for a Philippine command center. Your task is to analyze an incoming report of uncollected garbage and sequentially update rolling contextual summaries for its corresponding Barangay (neighborhood) and the City-wide Overall system.

---
INPUT CONTEXT:
1. Predetermined Report Type: {report_type.value}
2. Citizen-provided Notes (Read and translate any Tagalog, Bisaya, Cebuano, or other local Filipino dialects into English):
"{report_notes}"
3. Associated Image: (An attached multimodal image of the site, which may be absent or blank)

---
CURRENT HISTORICAL STATE:
Existing Barangay Analysis: "{barangay_analysis}"
Existing City-Wide Overall Analysis: "{overall_analysis}"

---
CRITICAL PROCESSING INSTRUCTIONS:
1. DATA AVAILABILITY EVALUATION (PRE-ANALYSIS):
    - If BOTH the report notes are empty/blank AND no image is present: Skip visual/textual evaluation. Your individual report analysis MUST state: "Report processed based solely on category metadata: <report type>."
    - If the image is PRESENT but the report notes are empty/blank: Base your analysis entirely on visual evidence from the image and the predetermined report type.
    - If the report notes are PRESENT but the image is missing/absent: Base your analysis entirely on the contextual data from the translated notes and the predetermined report type. Do not mention missing image context as an error; simply analyze the text.

2. INDIVIDUAL REPORT ANALYSIS: Synthesize the available data inputs. If an image is provided but does not contain uncollected garbage, explicitly state "INVALID REPORT: Image does not depict uncollected waste." Max limit: 5 sentences.

3. BARANGAY ANALYSIS UPDATE: Evaluate the existing Barangay Analysis string.
    - COLD START: If the string is empty, null, or "<content>", write a brand new foundational analysis for this Barangay based entirely on the current report's available data.
    - UPDATING: If a valid summary exists, integrate this new report's data into it if it changes the urgency, waste volume, or localized hazard profile. Otherwise, repeat the existing text exactly. Max limit: 5 sentences.

4. CITY-WIDE OVERALL ANALYSIS UPDATE: Evaluate the existing City-Wide Analysis string.
    - COLD START: If the string is empty, null, or "<content>", write a brand new foundational city summary based on the updated Barangay analysis.
    - UPDATING: If a valid city-wide summary exists, update it if this Barangay's situation introduces critical municipal priorities (e.g., city-wide flooding risks, toxic waste accumulation). Otherwise, repeat the existing text exactly. Max limit: 5 sentences.

---
OUTPUT FORMAT:
You must return a raw, syntactically valid JSON object matching the schema below. Do not wrap it in markdown block tags (like ```json), do not include trailing commas, and provide no conversational prose before or after the JSON.

{{
    "report_analysis": "String containing individual report analysis or fallback text.",
    "updated_barangay_analysis": "String containing the initial or updated barangay tracking analysis.",
    "updated_overall_analysis": "String containing the initial or updated city-wide tracking analysis."
}}"""

    payload = {
        "model": settings.OPENROUTER_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
    }

    if image_data_url:
        payload["messages"][0]["content"].append({
            "type": "image_url",
            "image_url": {
                "url": image_data_url
            }
        })
        logger.info("Image data url is present, appending to payload...")

    response = requests.post(
        url=settings.OPENROUTER_API_ENDPOINT,
        headers={
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        data=json.dumps(payload)
    )

    if response.status_code != 200:
        # raise HTTPException(status_code=502, detail=f"OpenRouter gateway error: {response.text}")
        raise Exception(f"OpenRouter gateway error: {response.text}")

    result = response.json()
    # logger.info(f"OpenRouter response: {result}")
    analysis_json_str = result["choices"][0]["message"]["content"]
    logger.info(f"OpenRouter raw JSON string response: {analysis_json_str}")

    analysis = dict()

    try:
        clean_json_string = analysis_json_str.replace("```json", "").replace("```", "").strip()
        analysis = json.loads(clean_json_string)
    except:
        raise Exception("Could not parse AI report analysis")

    analysis["barangay_id"] = barangay_id

    return analysis

# this function calls the previous function and is designed to be
# run as a backgorund task in order to be non-blocking for report uploads
def process_ai_report_analysis(report_id: int) -> None:
    with Session(db_engine) as session:
        report = session.get(Report, report_id)
        if not report:
            return

        try:
            analysis = analyze_garbage_report(report)

            # update immediate barangay report analysis
            if isinstance(analysis.get("updated_barangay_analysis"), str) and isinstance(analysis.get("barangay_id"), int):
                barangay = session.get(Barangay, analysis["barangay_id"])
                if barangay:
                    logger.info(f"Barangay with ID {analysis["barangay_id"]} found, proceeding with analysis update...")
                    barangay.ai_summary = analysis["updated_barangay_analysis"]
                    session.add(barangay)
                    session.commit()
                    logger.info(f"Completed analysis update of barangay with ID {analysis["barangay_id"]}")
                else:
                    logger.warning(f"Barangay with id {analysis["barangay_id"]} not found, skipping analysis update...")
            else:
                logger.warning("Updated barangay analysis data seems to be malformed, skipping analysis update entirely...")

            # update overall report analysis
            if isinstance(analysis.get("updated_overall_analysis"), str):
                summary = session.exec(select(Summary)).first()
                if not summary:
                    logger.info("Overall summary not initialized yet, proceeding with initialization...")
                    summary = Summary()
                summary.general_summary = analysis["updated_overall_analysis"]
                session.add(summary)
                session.commit()
                logger.info("Completed analysis update of overall report analysis")
            else:
                logger.warning("Updated overall analysis data seems to be malformed, skipping analysis update entirely...")

            report.ai_summary = analysis["report_analysis"]
            session.add(report)
            session.commit()
            logger.info(f"Finished processing analysis of report with ID {report_id}")

        except Exception as error:
            logger.fatal(f"An error occured while processing the AI report analysis: {error}")
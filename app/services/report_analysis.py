import base64
import requests
import json
import os

from fastapi import HTTPException
from typing import Any

from sqlmodel import Session, select, text

from app.schemas import ReportType, Report, Barangay, Summary, ReportCount, ReportTypeFreq
from app.services.database import db_engine
from app.config import settings

from shapely.geometry import Point, Polygon
from pyproj import Geod

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

def get_report_count(barangay_id: int = 0) -> int:
    with Session(db_engine) as session:
        query = text("SELECT COUNT(*) as report_count FROM reports")
        if barangay_id:
            query = text("SELECT COUNT(*) as report_count FROM reports WHERE under_barangay_id = :barangay_id")
        result = session.execute(query, {"barangay_id": barangay_id})
        return result.fetchone()._asdict()["report_count"]

def get_report_density(barangay_id: int = 0) -> float:
    with Session(db_engine) as session:
        report_count = get_report_count(barangay_id)

        area_sq_meters = 2_443_610_000
        if barangay_id:
            barangay = session.get(Barangay, barangay_id)
            if not barangay:
                return 0
            coords = [(long, lat) for lat, long in barangay.bounds_coords]
            polygon = Polygon(coords)
            geod = Geod(ellps="WGS84")
            raw_area, _ = geod.geometry_area_perimeter(polygon)
            area_sq_meters = abs(raw_area)

        return round(report_count / area_sq_meters, 3)

def get_barangays_with_most_reports() -> list[ReportCount]:
    with Session(db_engine) as session:
        query = text("""SELECT b.name as barangay_name, COUNT(r.under_barangay_id) as count
            FROM reports r JOIN barangays b ON b.barangay_id = r.under_barangay_id
            GROUP BY b.barangay_id, b.name ORDER BY count DESC LIMIT 10""")
        result = session.execute(query)
        rows = result.fetchall()
        report_counts = []
        for row in rows:
            row_dict = row._asdict()
            report_counts.append(ReportCount(
                barangay_name=row_dict["barangay_name"],
                count=row_dict["count"]
            ))
        return report_counts

def get_report_type_freq(barangay_id: int = 0) -> list[ReportTypeFreq]:
    with Session(db_engine) as session:
        query = text("SELECT type as report_type, COUNT(type) as count FROM reports GROUP BY type")
        if barangay_id:
            query = text("SELECT type as report_type, COUNT(type) as count FROM reports WHERE under_barangay_id = :barangay_id GROUP BY type")
        result = None
        if barangay_id:
            result = session.execute(query, {"barangay_id": barangay_id})
        else:
            result = session.execute(query)
        rows = result.fetchall()
        report_type_freqs = []
        for row in rows:
            row_dict = row._asdict()
            report_type_freqs.append(ReportTypeFreq(
                report_type=row_dict["report_type"],
                count=row_dict["count"]
            ))
        return report_type_freqs

def get_report_themes(barangay_id: int = 0) -> list[str]:
    with Session(db_engine) as session:
        if barangay_id:
            barangay = session.get(Barangay, barangay_id)
            if barangay:
                return barangay.report_themes
            else:
                return []
        else:
            summary = session.exec(select(Summary)).first()
            if not summary:
                summary = Summary(general_themes=[])
                session.add(summary)
                session.commit()
                session.refresh(summary)
            return summary.general_themes

def get_barangay_report_analysis(barangay_id: int) -> str:
    with Session(db_engine) as session:
        barangay = session.get(Barangay, barangay_id)
        if not barangay:
            raise Exception(f"Barangay with ID {barangay_id} not found")
        return barangay.report_summary if barangay.report_summary else ""

def get_general_report_analysis() -> str:
    with Session(db_engine) as session:
        summary = session.exec(select(Summary)).first()
        if not summary:
            summary = Summary(general_themes=[])
            session.add(summary)
            session.commit()
            session.refresh(summary)
        return summary.general_summary if summary.general_summary else ""

def get_barangay_themes(barangay_id: int) -> list[str]:
    with Session(db_engine) as session:
        barangay = session.get(Barangay, barangay_id)
        if not barangay:
            raise Exception(f"Barangay with ID {barangay_id} not found")
        return barangay.report_themes

def get_general_themes() -> list[str]:
    with Session(db_engine) as session:
        summary = session.exec(select(Summary)).first()
        if not summary:
            summary = Summary(general_themes=[])
            session.add(summary)
            session.commit()
            session.refresh(summary)
        return summary.general_themes

def get_barangay_id_of_loc(latitude: float, longitude: float) -> int:
    report_point = Point(longitude, latitude)
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

    barangay_id = report.under_barangay_id

    barangay_analysis = ""
    barangay_themes = []
    try:
        barangay_analysis = get_barangay_report_analysis(barangay_id)
        barangay_themes = get_barangay_themes(barangay_id)
    except Exception as error:
        logger.warning(f"Could not retrieve barangay analysis of barangay with id {barangay_id}\nError: {error}")

    overall_analysis = ""
    overall_themes = []
    try:
        overall_analysis = get_general_report_analysis()
        overall_themes = get_general_themes()
    except Exception as error:
        logger.warning(f"Could not retrieve overall reports analysis\nError: {error}")

    prompt = f"""\
You are an expert municipal data analyst and city triage inspector for a Philippine command center. Your task is to analyze an incoming report of uncollected garbage, extract its specific thematic issues, and sequentially update rolling contextual summaries and systemic themes for both its corresponding Barangay (neighborhood) and the City-wide Overall system.

---
INPUT CONTEXT:
1. Predetermined Report Type: "{report_type.value}"
2. Citizen-provided Notes (Read and translate any Tagalog, Bisaya, Cebuano, or other local Filipino dialects into English):
"{report_notes}"
3. Associated Image: (An attached multimodal image of the site, which may be absent or blank)

---
CURRENT HISTORICAL STATE:
1. Existing Barangay Analysis: "{barangay_analysis}"
2. Existing Barangay Themes: {barangay_themes}
3. Existing City-Wide Overall Analysis: "{overall_analysis}"
4. Existing City-Wide Overall Themes: {overall_themes}

---
CRITICAL PROCESSING INSTRUCTIONS:
1. DATA AVAILABILITY EVALUATION (PRE-ANALYSIS):
    - If BOTH the report notes are empty/blank AND no image is present: Skip visual/textual evaluation. Your individual report analysis MUST state: "Report processed based solely on category metadata: {{report type}}."
    - If the image is PRESENT but the report notes are empty/blank: Base your analysis entirely on visual evidence from the image and the predetermined report type.
    - If the report notes are PRESENT but the image is missing/absent: Base your analysis entirely on the contextual data from the translated notes and the predetermined report type. Do not mention missing image context as an error; simply analyze the text.

2. INDIVIDUAL REPORT ANALYSIS & THEME EXTRACTION:
    - Synthesize the available data inputs. If an image is provided but does not contain uncollected garbage, explicitly state "INVALID REPORT: Image does not depict uncollected waste." Max limit: 5 sentences.
    - Extract 1 to 3 concise, high-level themes from this specific report (e.g., "Public Health Risk", "Market Day Waste Surge", "Electronic Waste Contamination", "Blocked Waterways"). These will be returned directly in the `report_themes` array.

3. BARANGAY ANALYSIS & THEMATIC UPDATE:
    - ANALYSIS: Evaluate the existing Barangay Analysis string. If cold starting (empty or placeholder), generate a foundational summary. If updating, integrate new trends if they alter urgency or hazard profiles; otherwise, retain existing text. Max limit: 5 sentences.
    - THEMES UPDATE: Evaluate the extracted report themes against the `Existing Barangay Themes` list.
        - If an extracted theme introduces a conceptually NEW localized issue, append it to the list.
        - If it is conceptually similar or identical to an existing theme (e.g., "Drainage Clog" vs "Blocked Culverts"), DO NOT duplicate or add it. Retain the existing theme list exactly.

4. CITY-WIDE OVERALL ANALYSIS & THEMATIC UPDATE:
    - ANALYSIS: Evaluate the existing City-Wide Analysis string. If cold starting, generate a foundational city summary. If updating, modify it if the updated Barangay tracking introduces macro municipal priorities (e.g., city-wide flooding risks, institutional collection failures). Max limit: 5 sentences.
    - THEMES UPDATE: Evaluate the updated Barangay themes against the `Existing City-Wide Overall Themes` list.
        - If a theme represents a distinct, macro-level systemic trend affecting multiple regions, append it to the city-wide list.
        - If it is redundant, highly similar, or too hyper-localized to matter at a city scale, DO NOT modify the list.

---
OUTPUT FORMAT:
You must return a raw, syntactically valid JSON object matching the schema below. Do not wrap it in markdown block tags (like ```json), do not include trailing commas, and provide no conversational prose before or after the JSON.

{{
    "report_analysis": "String containing individual report analysis or fallback text.",
    "report_themes": ["Array", "of", "strings", "extracted", "specifically", "from", "this", "single", "report"],
    "updated_barangay_analysis": "String containing the initial or updated barangay tracking analysis.",
    "updated_barangay_themes": ["Array", "of", "strings", "representing", "the", "deduplicated", "barangay", "themes"],
    "updated_overall_analysis": "String containing the initial or updated city-wide tracking analysis.",
    "updated_overall_themes": ["Array", "of", "strings", "representing", "the", "deduplicated", "city", "wide", "themes"]
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
                    barangay.report_summary = analysis["updated_barangay_analysis"]
                    session.add(barangay)
                    session.commit()
                    logger.info(f"Completed analysis update of barangay with ID {analysis["barangay_id"]}")
                else:
                    logger.warning(f"Barangay with ID {analysis["barangay_id"]} not found, skipping analysis update...")
            else:
                logger.warning("Updated barangay analysis data seems to be malformed, skipping analysis update entirely...")

            # update immediate barangay thematic analysis
            if isinstance(analysis.get("updated_barangay_themes"), list) and isinstance(analysis.get("barangay_id"), int):
                barangay = session.get(Barangay, analysis["barangay_id"])
                if barangay:
                    logger.info(f"Barangay with ID {analysis["barangay_id"]} found, proceeding with thematic analysis update...")
                    barangay.report_themes = analysis["updated_barangay_themes"]
                    session.add(barangay)
                    session.commit()
                    logger.info(f"Completed thematic analysis update of barangay with ID {analysis["barangay_id"]}")
                else:
                    logger.warning(f"Barangay with ID {analysis["barangay_id"]} not found, skipping thematic analysis update...")

            # update overall report analysis
            if isinstance(analysis.get("updated_overall_analysis"), str):
                summary = session.exec(select(Summary)).first()
                if not summary:
                    logger.info("Overall summary not initialized yet, proceeding with initialization...")
                    summary = Summary(general_themes=[])
                summary.general_summary = analysis["updated_overall_analysis"]
                session.add(summary)
                session.commit()
                logger.info("Completed analysis update of overall report analysis")
            else:
                logger.warning("Updated overall analysis data seems to be malformed, skipping analysis update entirely...")

            # update overall thematic analysis
            if isinstance(analysis.get("updated_overall_themes"), list):
                summary = session.exec(select(Summary)).first()
                if not summary:
                    logger.info("Overall summary not initialized yet, proceeding with initialization...")
                    summary = Summary(general_themes=[])
                summary.general_themes = analysis["updated_overall_themes"]
                session.add(summary)
                session.commit()
                logger.info("Completed thematic analysis update of overall report thematic analysis")
            else:
                logger.warning("Updated overall thematic analysis data seems to be malformed, skipping thematic analysis updated entirely...")

            report_updated = False

            if isinstance(analysis.get("report_analysis"), str):
                report.report_summary = analysis["report_analysis"]
                report_updated = True
            if isinstance(analysis.get("report_themes"), str):
                report.report_themes = analysis["report_themes"]
                report_updated = True

            if report_updated:
                session.add(report)
                session.commit()

            logger.info(f"Finished processing analysis of report with ID {report_id}")

        except Exception as error:
            logger.fatal(f"An error occured while processing the AI report analysis: {error}")
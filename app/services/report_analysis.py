import base64
import requests
import json
import os
import sys

from fastapi import HTTPException
from typing import Any

from sqlmodel import Session, select, text

from app.schemas import ReportType, Report, Barangay, Summary, ReportCount, ReportTypeFreq, Theme
from app.services.database import db_engine
from app.config import settings

from shapely.geometry import Point, Polygon
from pyproj import Geod

import boto3
from botocore.config import Config

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

bedrock = boto3.client(
    "bedrock-runtime",
    region_name="ap-southeast-1",
    config=Config(read_timeout=3600)
)

PROMPT_TEMPLATE = """\
You are an expert municipal data analyst and city triage inspector for a Philippine command center. Your task is to analyze an incoming report of uncollected garbage, extract its specific thematic issues along with descriptive qualitative codes, and sequentially update rolling contextual summaries and systemic themes for both its corresponding Barangay (neighborhood) and the City-wide Overall system.

---
INPUT CONTEXT:
1. Predetermined Report Type: "{report_type}"
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
    - Extract 1 to 3 structured themes from this specific report. Each theme must be an object containing a broad "title" (e.g., "Public Health Risk") and an array of specific, granular "codes" derived from the raw text/image data (e.g., ["odors", "swarming-flies", "vermin-sighting"]). These will be returned directly in the `report_themes` array.

3. BARANGAY ANALYSIS & THEMATIC UPDATE:
    - ANALYSIS: Evaluate the existing Barangay Analysis string. If cold starting (empty or placeholder), generate a foundational summary. If updating, integrate new trends if they alter urgency or hazard profiles; otherwise, retain existing text. Max limit: 5 sentences.
    - THEMES UPDATE: Evaluate the extracted report themes against the `Existing Barangay Themes` objects.
        - If an extracted theme's title is conceptually NEW to the Barangay, append the whole object (title and codes) to the list.
        - If the theme's title is conceptually similar or identical to an existing theme title, DO NOT add a duplicate theme object. Instead, merge any NEW unique codes into that existing theme's "codes" array, keeping the codes deduplicated.

4. CITY-WIDE OVERALL ANALYSIS & THEMATIC UPDATE:
    - ANALYSIS: Evaluate the existing City-Wide Analysis string. If cold starting, generate a foundational city summary. If updating, modify it if the updated Barangay tracking introduces macro municipal priorities (e.g., city-wide flooding risks, institutional collection failures). Max limit: 5 sentences.
    - THEMES UPDATE: Evaluate the updated Barangay themes against the `Existing City-Wide Overall Themes` objects.
        - If a theme title represents a distinct, macro-level systemic trend affecting multiple regions, append the object to the city-wide list.
        - If the theme title already exists, merge any new systemic codes into its existing "codes" array. If it is redundant or too hyper-localized to matter at a city scale, DO NOT modify the list.

---
OUTPUT FORMAT:
You must return a raw, syntactically valid JSON object matching the schema below. Do not wrap it in markdown block tags (like ```json), do not include trailing commas, and provide no conversational prose before or after the JSON.

{{
    "report_analysis": "String containing individual report analysis or fallback text.",
    "report_themes": [
        {{
            "title": "Theme Title Here",
            "codes": ["code1", "code2", "code3"]
        }}
    ],
    "updated_barangay_analysis": "String containing the initial or updated barangay tracking analysis.",
    "updated_barangay_themes": [
        {{
            "title": "Theme Title Here",
            "codes": ["code1", "code2", "code3"]
        }}
    ],
    "updated_overall_analysis": "String containing the initial or updated city-wide tracking analysis.",
    "updated_overall_themes": [
        {{
            "title": "Theme Title Here",
            "codes": ["code1", "code2", "code3"]
        }}
    ]
}}"""

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
            GROUP BY b.barangay_id, b.name ORDER BY count DESC""")
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

def get_report_themes(barangay_id: int = 0) -> list[Theme]:
    themes = []
    with Session(db_engine) as session:
        if barangay_id:
            barangay = session.get(Barangay, barangay_id)
            if barangay:
                for theme in barangay.report_themes:
                    themes.append(Theme(title=theme.get("title", ""), codes=theme.get("codes", [])))
            return themes
        else:
            summary = session.exec(select(Summary)).first()
            if not summary:
                summary = Summary(general_themes=[])
                session.add(summary)
                session.commit()
                session.refresh(summary)
            for theme in summary.general_themes:
                themes.append(Theme(title=theme.get("title", ""), codes=theme.get("codes", [])))
            return themes

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

def get_barangay_themes(barangay_id: int) -> list[Theme]:
    themes = []
    with Session(db_engine) as session:
        barangay = session.get(Barangay, barangay_id)
        if not barangay:
            raise Exception(f"Barangay with ID {barangay_id} not found")
        for theme in barangay.report_themes:
            themes.append(Theme(title=theme.get("title", ""), codes=theme.get("codes", [])))
    return themes

def get_general_themes() -> list[Theme]:
    themes = []
    with Session(db_engine) as session:
        summary = session.exec(select(Summary)).first()
        if not summary:
            summary = Summary(general_themes=[])
            session.add(summary)
            session.commit()
            session.refresh(summary)
        for theme in summary.general_themes:
            themes.append(Theme(title=theme.get("title", ""), codes=theme.get("codes", [])))
    return themes

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

def analyze_garbage_report(report: Report) -> dict[str, Any]:
    report_type = report.type
    report_notes = report.notes
    report_image_url = report.image_url

    if not report.notes and not report.image_url:
        raise Exception("No report notes or image to proceed with analysis")

    # when using s3, remove byte reading and pass asset link directly
    data_format = ""
    report_image_bytes = b""
    if report_image_url:
        logging.info("Image url present, reading image...")
        with open(report_image_url, "rb") as file:
            report_image_bytes = file.read()
        data_format = os.path.splitext(report_image_url)[1][1:]

    if not report_notes:
       report_notes = ""

    barangay_id = report.under_barangay_id

    barangay_analysis = get_barangay_report_analysis(barangay_id)
    barangay_themes = []
    _barangay_themes = get_barangay_themes(barangay_id)
    for theme in _barangay_themes:
        barangay_themes.append(dict(theme))

    overall_analysis = get_general_report_analysis()
    overall_themes = []
    _overall_themes = get_general_themes()
    for theme in _overall_themes:
        overall_themes.append(dict(theme))

    prompt = PROMPT_TEMPLATE.format(
        report_type=report_type.value,
        report_notes=report_notes,
        barangay_analysis=barangay_analysis,
        barangay_themes=barangay_themes,
        overall_analysis=overall_analysis,
        overall_themes=overall_themes
    )

    messages = [
        {
            "role": "user",
            "content": []
        }
    ]

    if report_image_bytes:
        messages[0]["content"].append({
            "image": {
                "format": "jpeg",
                "source": {
                    "bytes": report_image_bytes
                }
            }
        })

    messages[0]["content"].append({
        "text": prompt
    })

    response = bedrock.converse(
        modelId="global.amazon.nova-2-lite-v1:0",
        messages=messages
    )

    analysis = ""
    for content in response["output"]["message"]["content"]:
        if "text" in content:
            analysis += content["text"]

    analysis = analysis.replace("```json", "").replace("```", "").strip()
    analysis_json = json.loads(analysis)

    logger.info(f"Analysis output: {analysis}")

    analysis_json["barangay_id"] = barangay_id

    return analysis_json

# def analyze_garbage_report(report: Report) -> dict[str, Any]:
#     report_type = report.type
#     report_notes = report.notes
#     report_image_url = report.image_url
#
#     if report_notes is None and report_image_url is None:
#         raise Exception("No report notes or image to proceed with analysis")
#
#     image_data_url = ""
#     image_encoded_string = ""
#
#     if report_image_url:
#         try:
#             with open(report_image_url, "rb") as file:
#                 image_encoded_string = base64.b64encode(file.read()).decode("utf-8")
#             file_extension = os.path.splitext(report_image_url)[1][1:]
#             image_data_url = f"data:image/{file_extension};base64,{image_encoded_string}"
#             logger.info(f"Image encoded into url with .{file_extension} file extension and {len(image_encoded_string)} characters encoded")
#         except:
#             raise Exception(f"Failed to read image {report_image_url} for AI analysis")
#
#     if not report_notes:
#         report_notes = ""
#
#     barangay_id = report.under_barangay_id
#
#     barangay_analysis = ""
#     barangay_themes = []
#     try:
#         barangay_analysis = get_barangay_report_analysis(barangay_id)
#         _barangay_themes = get_barangay_themes(barangay_id)
#         for theme in _barangay_themes:
#             barangay_themes.append(dict(theme))
#     except Exception as error:
#         logger.warning(f"Could not retrieve barangay analysis of barangay with id {barangay_id}\nError: {error}")
#
#     overall_analysis = ""
#     overall_themes = []
#     try:
#         overall_analysis = get_general_report_analysis()
#         _overall_themes = get_general_themes()
#         for theme in _overall_themes:
#             overall_themes.append(dict(theme))
#     except Exception as error:
#         logger.warning(f"Could not retrieve overall reports analysis\nError: {error}")
#
#     prompt = PROMPT_TEMPLATE.format(
#         report_type=report_type.value,
#         report_notes=report_notes,
#         barangay_analysis=barangay_analysis,
#         barangay_themes=barangay_themes,
#         overall_analysis=overall_analysis,
#         overall_themes=overall_themes
#     )
#
#     payload = {
#         "model": settings.OPENROUTER_MODEL,
#         "messages": [
#             {
#                 "role": "user",
#                 "content": [
#                     {
#                         "type": "text",
#                         "text": prompt
#                     }
#                 ]
#             }
#         ]
#     }
#
#     if image_data_url:
#         payload["messages"][0]["content"].append({
#             "type": "image_url",
#             "image_url": {
#                 "url": image_data_url
#             }
#         })
#         logger.info("Image data url is present, appending to payload...")
#
#     response = requests.post(
#         url=settings.OPENROUTER_API_ENDPOINT,
#         headers={
#             "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
#             "Content-Type": "application/json"
#         },
#         data=json.dumps(payload)
#     )
#
#     if response.status_code != 200:
#         raise Exception(f"OpenRouter gateway error: {response.text}")
#
#     result = response.json()
#     # logger.info(f"AI response: {result}")
#     analysis_json_str = result["choices"][0]["message"]["content"]
#     logger.info(f"AI raw JSON string response: {analysis_json_str}")
#
#     analysis = dict()
#
#     try:
#         clean_json_string = analysis_json_str.replace("```json", "").replace("```", "").strip()
#         analysis = json.loads(clean_json_string)
#     except:
#         raise Exception("Could not parse AI report analysis")
#
#     analysis["barangay_id"] = barangay_id
#
#     return analysis

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
                    barangay.report_themes = []
                    for theme in analysis["updated_barangay_themes"]:
                        if not theme.get("title") or not theme.get("codes"):
                            continue
                        barangay.report_themes.append(theme)
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
                summary.general_themes = []
                for theme in analysis["updated_overall_themes"]:
                    if not theme.get("title") or not theme.get("codes"):
                        continue
                    summary.general_themes.append(theme)
                session.add(summary)
                session.commit()
                logger.info("Completed thematic analysis update of overall report thematic analysis")
            else:
                logger.warning("Updated overall thematic analysis data seems to be malformed, skipping thematic analysis updated entirely...")

            report_updated = False

            if isinstance(analysis.get("report_analysis"), str):
                report.report_summary = analysis["report_analysis"]
                report_updated = True
            if isinstance(analysis.get("report_themes"), list):
                report.report_themes = []
                for theme in analysis["report_themes"]:
                    if not theme.get("title") or not theme.get("codes"):
                        continue
                    report.report_themes.append(theme)
                report_updated = True

            if report_updated:
                session.add(report)
                session.commit()

            logger.info(f"Finished processing analysis of report with ID {report_id}")

        except Exception as error:
            traceback = sys.exc_info()[2]
            logger.fatal(f"An error occured while processing the AI report analysis: {error} @ line {traceback.tb_lineno}")
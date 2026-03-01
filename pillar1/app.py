import os
import re
import json
import pdfplumber
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# =========================================================
# CONFIG
# =========================================================

st.set_page_config(
    page_title="Trademark PDF Adaptive Parser",
    layout="wide"
)

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

# =========================================================
# 1️⃣ TEXT NORMALIZATION
# =========================================================

def normalize_text(raw_text: str) -> str:
    raw_text = re.sub(r"\r", "", raw_text)
    raw_text = re.sub(r"\n{2,}", "\n", raw_text)
    raw_text = re.sub(r"[ \t]+", " ", raw_text)
    return raw_text.strip()

# SECTION SEGMENTER
# =========================================================

SECTION_HEADERS = [
    "Trademark details",
    "Owner information",
    "Goods and services",
    "Specimen Information",
    "Additional statements",
    "Attorney information",
    "Fee information",
    "Declaration and signature"
]
def segment_sections(text: str):
    sections = {}
    current = "header"
    sections[current] = ""

    for line in text.split("\n"):
        header_match = next((h for h in SECTION_HEADERS if h.lower() in line.lower()), None)

        if header_match:
            current = header_match
            sections[current] = ""
        else:
            sections[current] += line + "\n"

    return sections

# FIELD EXTRACTION HELPERS
# =========================================================

def extract(pattern, text):
    match = re.search(pattern, text, re.I | re.DOTALL)
    return match.group(1).strip() if match else ""


def detect_mark_type(header_text):
    if "Combination of wording and a design" in header_text:
        return "design_plus_words"
    if "Standard Characters Claimed" in header_text:
        return "standard_character"
    return "unknown"

# =========================================================
# 2️⃣ FLEXIBLE FIELD EXTRACTOR
# =========================================================

def flexible_extract(patterns, text):
    for pattern in patterns:
        match = re.search(pattern, text, re.I | re.DOTALL)
        if match:
            return match.group(1).strip()
    return ""


# =========================================================
# 3️⃣ INTELLIGENT CLASS DETECTOR
# =========================================================
# =========================================================
# FIXED PARSER VERSION (MINIMAL CHANGES)
# =========================================================

def extract_classes(goods_section: str):

    class_blocks = re.findall(
        r"International Class (\d+)(.*?)(?=International Class|\Z)",
        goods_section,
        re.I | re.DOTALL
    )

    results = []

    for class_number, block in class_blocks:

        identification = extract(
            r"Identification of goods and services\s*(.*?)(?=Specimen Information|\Z)",
            block
        )

        filing_basis = extract(
            r"Filing basis:\s*(Section\s+[0-9a-z\(\)]+)",
            block
        )

        results.append({
            "class_number": int(class_number),
            "identification": identification.strip(),
            "specimen_type": "",
            "specimen_description": "",
            "fee_paid": True,
            "filing_basis": filing_basis.replace("Section ", "") if filing_basis else "",
            "date_of_first_use": "",
            "date_of_first_use_commerce": ""
        })

    return results


def parse_trademark_pdf(uploaded_file):

    raw_text = ""

    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                raw_text += text + "\n"

    cleaned = normalize_text(raw_text)
    sections = segment_sections(cleaned)

    header_text = sections.get("header", "")
    trademark_section = sections.get("Trademark details", "")
    goods_section = sections.get("Goods and services", "")
    specimen_section = sections.get("Specimen Information", "")
    fee_section = sections.get("Fee information", "")

    # CORE FIELDS
    serial_number = extract(r"Serial number:\s*(\d+)", header_text)
    filing_date = extract(r"Filing date:\s*(.*?)\n", header_text)
    mark_literal = extract(r"Literal element\s*(.*?)\n", trademark_section)

    # FIXED: detect mark type from trademark section
    mark_type = detect_mark_type(trademark_section)

    # FIXED: allow optional *
    owner_name = extract(r"\*?Name\s*(.*?)\n", sections.get("Owner information", ""))

    total_fee = extract(r"Total fees paid\s*\$\s*([\d\.]+)", fee_section)

    # SPECIMEN
    first_use_anywhere = extract(r"First use anywhere date\s*(.*?)\n", specimen_section)
    first_use_commerce = extract(r"First use in commerce date\s*(.*?)\n", specimen_section)
    specimen_description = extract(r"Description\s*(.*?)\n", specimen_section)
    specimen_url = extract(r"URL\s*(.*?)\n", specimen_section)

    # CLASSES
    classes = extract_classes(goods_section)

    for cls in classes:
        cls["date_of_first_use"] = first_use_anywhere
        cls["date_of_first_use_commerce"] = first_use_commerce
        cls["specimen_description"] = specimen_description
        cls["specimen_type"] = "website" if specimen_url else ""

    structured = {
        "applicant_name": owner_name,
        "mark_text": mark_literal,
        "mark_type": mark_type,
        "filing_date": filing_date,
        "nice_edition_claimed": "12th",
        "application_serial": serial_number,
        "filing_type": "TEAS_PLUS",
        "fees_paid_count": len(classes),
        "total_fee_paid": float(total_fee) if total_fee else 0.0,
        "notes": "",
        "classes": classes
    }

    return structured


# =========================================================
# UI
# =========================================================

st.title("Trademark PDF Adaptive Parser")

uploaded_file = st.file_uploader("Upload Trademark Application PDF", type=["pdf"])

if uploaded_file:

    if st.button("Extract Structured Data"):

        structured_data = parse_trademark_pdf(uploaded_file)

        st.success("Extraction Complete")
        st.json(structured_data)

        st.session_state["parsed_json"] = structured_data


# =========================================================
# SEND TO BACKEND
# =========================================================
# =========================================================
# DIRECT PILLAR 1 INTEGRATION (MINIMAL)
# =========================================================

from main import assess_trademark_application   # <-- IMPORTANT

if "parsed_json" in st.session_state:

    if st.button("Run Pillar 1 Classification Assessment"):

        result = assess_trademark_application(
            st.session_state["parsed_json"]
        )

        st.subheader("Pillar 1 Report (§1401 Classification)")
        st.text_area("Classification Report",
                     result["report"],
                     height=500)

        st.subheader("Quick Summary")
        st.json(result["summary"])
# if "parsed_json" in st.session_state:

#     if st.button("Run Examination Engine"):

#         try:
#             response = requests.post(
#                 f"{BACKEND_URL}/analyze",
#                 json={"data": st.session_state["parsed_json"]},
#                 timeout=120
#             )

#             if response.status_code == 200:
#                 result = response.json()
#                 st.subheader("Examination Report")
#                 st.text_area("Result", result.get("analysis", ""), height=500)
#             else:
#                 st.error(f"Backend error: {response.text}")

#         except Exception as e:
#             st.error(f"Connection error: {str(e)}")
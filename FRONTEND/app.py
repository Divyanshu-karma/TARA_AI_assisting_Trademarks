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
    raw_text = re.sub(r"Page\s+\d+\s+of\s+\d+", "", raw_text, flags=re.I)
    raw_text = re.sub(r"United States Patent.*?Trademark Office", "", raw_text, flags=re.I)
    raw_text = re.sub(r"\n(?=[a-z])", " ", raw_text)
    raw_text = re.sub(r"\n+", "\n", raw_text)
    raw_text = re.sub(r"[ \t]+", " ", raw_text)
    return raw_text.strip()


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

def extract_classes_adaptive(text):

    class_patterns = [
        r"(International\s+Class\s+\d+[:\-]?\s*)(.*?)(?=International\s+Class|\Z)",
        r"(Class\s+\d+[:\-]?\s*)(.*?)(?=Class\s+\d+|\Z)",
        r"(IC\s*0*\d+[:\-]?\s*)(.*?)(?=IC\s*0*\d+|\Z)"
    ]

    results = []

    for pattern in class_patterns:
        matches = re.findall(pattern, text, re.I | re.DOTALL)

        for header, description in matches:
            class_number = re.search(r"\d+", header).group()
            clean_desc = description.strip().replace("\n", " ")

            clean_desc = re.sub(r"First Use.*", "", clean_desc, flags=re.I)
            clean_desc = re.sub(r"Use in Commerce.*", "", clean_desc, flags=re.I)

            results.append({
                "class_number": int(class_number),
                "identification": clean_desc.strip(),
                "specimen_type": "",
                "specimen_description": "",
                "fee_paid": True,
                "filing_basis": "1(a)",
                "date_of_first_use": "",
                "date_of_first_use_commerce": ""
            })

        if results:
            break

    return results


# =========================================================
# 4️⃣ ADAPTIVE PDF PARSER
# =========================================================

def parse_trademark_pdf_adaptive(uploaded_file):

    raw_text = ""

    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                raw_text += page_text + "\n"

    cleaned_text = normalize_text(raw_text)

    serial_number = flexible_extract([
        r"Serial\s+Number[:\s]+([\d/]+)",
        r"SN[:\s]+([\d/]+)"
    ], cleaned_text)

    registration_number = flexible_extract([
        r"Registration\s+Number[:\s]+([\d/]+)",
        r"Reg\.\s*No\.?[:\s]+([\d/]+)"
    ], cleaned_text)

    mark_literal = flexible_extract([
        r"Mark[:\s]+([A-Z0-9\-\& ]+)",
        r"Literal\s+Element[:\s]+(.+)"
    ], cleaned_text)

    owner_name = flexible_extract([
        r"Owner[:\s]+(.+)",
        r"Applicant[:\s]+(.+)"
    ], cleaned_text)

    entity = flexible_extract([
        r"Entity\s+Type[:\s]+(.+)",
        r"Legal\s+Entity[:\s]+(.+)"
    ], cleaned_text)

    citizenship = flexible_extract([
        r"Citizenship[:\s]+(.+)",
        r"Country\s+of\s+Organization[:\s]+(.+)"
    ], cleaned_text)

    filing_basis = "1(a)" if "use in commerce" in cleaned_text.lower() else "1(b)"

    classes = extract_classes_adaptive(cleaned_text)

    if not classes:
        class_match = re.search(r"International\s+Class\s+(\d+)", cleaned_text)
        goods_match = flexible_extract([
            r"Goods\s+and\s+Services[:\s]+(.+)"
        ], cleaned_text)

        if class_match:
            classes = [{
                "class_number": int(class_match.group(1)),
                "identification": goods_match,
                "specimen_type": "",
                "specimen_description": "",
                "fee_paid": True,
                "filing_basis": filing_basis,
                "date_of_first_use": "",
                "date_of_first_use_commerce": ""
            }]

    structured = {
        "applicant_name": owner_name,
        "mark_text": mark_literal,
        "mark_type": "standard_character",
        "filing_date": "",
        "nice_edition_claimed": "12th",
        "application_serial": serial_number,
        "filing_type": "TEAS_PLUS",
        "fees_paid_count": len(classes),
        "total_fee_paid": 0.0,
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

        structured_data = parse_trademark_pdf_adaptive(uploaded_file)

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
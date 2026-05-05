import google.generativeai as genai
import streamlit as st
import json

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

model = genai.GenerativeModel("gemini-3-flash-preview")

def parse_amount(value):
    if value is None:
        return 0.0

    if isinstance(value, (int, float)):
        return float(value)

    # Remove commas and spaces
    value = str(value).replace(",", "").strip()

    try:
        return float(value)
    except:
        return 0.0

def extract_invoice_data(file_bytes):
    prompt = """
    Extract structured invoice data from the document.

    Return JSON in this exact format:
    {
      "invoice_num": "",
      "invoice_date": "",
      "invoice_amount": "",
      "currency": "",
      "vendor_num": "",
      "vendor_site": "",
      "description": "",
      "po_number": ""
    }

    Ensure date format: YYYY-MM-DD
    """

    response = model.generate_content(
        [
            prompt,
            {"mime_type": "application/pdf", "data": file_bytes}
        ]
    )
    print("Raw Response from model:", response.text)  # Debugging line
    try:
        text = response.text.strip()
        json_start = text.find("{")
        json_end = text.rfind("}") + 1
        return json.loads(text[json_start:json_end])
    except Exception as e:
        return {"error": str(e), "raw": response.text}
    
import requests
import streamlit as st
from requests.auth import HTTPBasicAuth
import random

def post_invoice_to_oracle(data):
    url = st.secrets["ORACLE_URL"]

    # Generate unique invoice ID
    invoice_id = random.randint(100000, 999999)

    invoice_date = data.get("invoice_date", "2024-01-01")

    payload = {
        "IMPORT_INVOICE_Input": {
            "RESTHeader": {
                "Responsibility": "PAYABLES_MANAGER",
                "RespApplication": "SQLAP",
                "SecurityGroup": "STANDARD",
                "NLSLanguage": "AMERICAN",
                "Language": "US",
                "Org_Id": "204"
            },
            "InputParameters": {
                "P_USER_ID": 1014748,
                "P_RESP_ID": 50554,
                "P_RESP_APPL_ID": 200,
                "P_INVOICE_ID": invoice_id,
                "P_INVOICE_NUM": data.get("invoice_num"),
                "P_INVOICE_DATE": invoice_date + "T00:00:00",
                "P_INVOICE_TYPE": "Standard",
                "P_INVOICE_AMOUNT": parse_amount(data.get("invoice_amount")),
                "P_CURRENCY_CODE": data.get("currency", "USD"),
                "P_VENDOR_NUM": data.get("vendor_num"),
                "P_VENDOR_SITE": data.get("vendor_site"),
                "P_ORG_ID": 204,
                "P_DESCRIPTION": data.get("description"),
                "P_PO_NUMBER": data.get("po_number"),
                "P_LINE_NUMBER": 1,
                "P_LINE_TYPE": "ITEM",
                "P_LINE_AMOUNT": parse_amount(data.get("invoice_amount")),
                "P_DIST_CCID": 123456,
                "P_ACCOUNTING_DATE": invoice_date + "T00:00:00"
            }
        }
    }

    response = requests.post(
        url,
        json=payload,
        auth=HTTPBasicAuth(
            st.secrets["ORACLE_USERNAME"],
            st.secrets["ORACLE_PASSWORD"]
        ),
        headers={"Content-Type": "application/json"}
    )

    return response.status_code, response.text, payload


import streamlit as st

st.set_page_config(page_title="Invoice Automation", layout="wide")
col1, col_spacer, col2 = st.columns([1, 2, 1])

with col1:
    st.image("qahtani.png", width=100)

with col2:
    st.image("OfficeFlow Ai-01-01.png", width=100)

st.title("📄 AI Invoice Processing Oracle EBS Integration")

uploaded_file = st.file_uploader("Upload Invoice (PDF)", type=["pdf"])

if uploaded_file:
    file_bytes = uploaded_file.read()

    st.info("Extracting data...")

    extracted_data = extract_invoice_data(file_bytes)

    if "error" in extracted_data:
        st.error("Extraction failed")
        st.text(extracted_data)
    else:
        st.success("Extraction Complete")

        st.subheader("📊 Extracted Data (Editable)")

        # Editable fields (VERY IMPORTANT in real scenarios)
        extracted_data["invoice_num"] = st.text_input(
            "Invoice Number", extracted_data.get("invoice_num", "")
        )

        extracted_data["invoice_date"] = st.text_input(
            "Invoice Date (YYYY-MM-DD)", extracted_data.get("invoice_date", "")
        )

        extracted_data["invoice_amount"] = st.text_input(
            "Invoice Amount", extracted_data.get("invoice_amount", "")
        )

        extracted_data["currency"] = st.text_input(
            "Currency", extracted_data.get("currency", "USD")
        )

        extracted_data["vendor_num"] = st.text_input(
            "Vendor Number", extracted_data.get("vendor_num", "")
        )

        extracted_data["vendor_site"] = st.text_input(
            "Vendor Site", extracted_data.get("vendor_site", "")
        )

        extracted_data["description"] = st.text_area(
            "Description", extracted_data.get("description", "")
        )

        extracted_data["po_number"] = st.text_input(
            "PO Number", extracted_data.get("po_number", "")
        )

        st.subheader("🔍 Final JSON Preview")
        st.json(extracted_data)

        #if st.button("🚀 Post to Oracle"):
        with st.spinner("Sending to Oracle..."):
            status, response, payload = post_invoice_to_oracle(extracted_data)

        st.subheader("📡 Oracle Response")
        st.write("Status Code:", status)
        st.text(response)

        # Debug payload (VERY useful for ISG issues)
        with st.expander("📦 Payload Sent to Oracle"):
            st.json(payload)

        if status == 200:
            st.success("Invoice successfully posted!")
        else:
            st.error("Failed to post invoice")
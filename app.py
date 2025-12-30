import streamlit as st
import speech_recognition as sr
from datetime import datetime
import unicodedata
import re
import firebase_admin
from firebase_admin import credentials, db
from dotenv import load_dotenv
import os


load_dotenv()
Api_key = os.getenv("GROQ_API_KEY")
database_key = os.getenv("FIREBASE_JSON_PATH")


# Initialize Firebase only once
if not firebase_admin._apps:
    cred = credentials.Certificate(database_key)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://udhar-system-be29b-default-rtdb.firebaseio.com/'
    })

# Firebase functions
def send_to_firebase(data):
    ref = db.reference("transactions")
    ref.push(data)

def get_customer_udhaar(name):
    # Normalize & standardize search name
    search_name = unicodedata.normalize('NFC', name.strip()).lower()

    ref = db.reference('transactions')
    all_data = ref.get()

    udhar_total = 0
    paid_total = 0
    udhar_records = []
    paid_records = []

    if all_data:
        for key, record in all_data.items():

            raw_name = record.get('customer_name') or record.get('name', '')
            rec_name = unicodedata.normalize('NFC', raw_name.strip()).lower()

            if rec_name == search_name:
                amount = int(record.get('amount', 0))

                if record.get('type') == 'Udhar':
                    udhar_records.append(record)
                    udhar_total += amount

                elif record.get('type') == 'Paid':
                    paid_records.append(record)
                    paid_total += amount

    return {
        'udhar_records': udhar_records,
        'paid_records': paid_records,
        'net_balance': udhar_total - paid_total,
        'udhar_total': udhar_total,
        'paid_total': paid_total
    }



def get_voice_text(timeout=6, lang='hi-IN'):
    r = sr.Recognizer()
    with sr.Microphone() as source:
        audio = r.listen(source, timeout=timeout)
    text = r.recognize_google(audio, language=lang)
    return text


# Extract info from speech (Rule Based)
def extract_info(text):
    t = text.lower()
    now = datetime.now()
    words = t.split()
    
    name = ""
    if "ने" in words:
        ne_index = words.index("ने")
        name = " ".join(words[:ne_index])
    name = " ".join(w.capitalize() for w in name.split())

    amount_match = re.search(r"\b(\d{1,5})\b", t)
    amount = int(amount_match.group(1)) if amount_match else 0

    item = ""
    if "वापस" in t or "दिया" in t or "दीया" in t or "दिए" in t:
        type = "Paid"
        item = "उधार चुकाया"

    elif "उधार" in t or "उधर" in t or "udhar" in t:
        type = "Udhar"
        item_match = re.search(r"का\s+(.*?)\s+(उधार|उधर)", t)
        if item_match:
            item = item_match.group(1).strip()
    else:
        type = "Nagat"
        item_match = re.search(r"का\s+(.*?)\s+(लिया)", t)
        if item_match:
            item = item_match.group(1).strip()
    return {
        'name': name.capitalize(),
        'amount': amount,
        'item': item,
        'type': type,
        'date': now.strftime("%Y-%m-%d %H:%M:%S")
    }

from groq import Groq
import json

# Initialize Groq Client
groq_client = Groq(
    api_key=Api_key
)

# Extract info from speech (Groq LLM)
def extract_udhar_info(text):
    prompt = f"""
Extract the following information from this text and return JSON ONLY:

Fields:
- customer_name
- item
- amount (numeric value only, no words)
- type:
  - "Udhar" → if 'udhar' word present
  - "Paid" → if payment done (500 chukaya / wapas)
  - "Nagat" → normal transaction

Text: "{text}"
"""

    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    raw_text = response.choices[0].message.content.strip()
    print("Raw Response:", raw_text)

    try:
        if raw_text.startswith("```"):
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()

        data = json.loads(raw_text)
        data["date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return data

    except Exception as e:
        print("Groq Parsing Error:", e)
        return extract_info(text)


# Streamlit GUI
st.set_page_config(page_title="📒 SmartKhata", layout="centered")
st.title("🗣️ SmartKhata System")

# Voice input and confirmation
if st.button("🎙️ Speak"):
    with st.spinner("कृपया बोलें..."):
        try:
            text = get_voice_text()
            extracted = extract_udhar_info(text)
            st.session_state["extracted_data"] = extracted  # Save in session state
            st.success("📢 आपने कहा:")
        except Exception as e:
            st.error(f"❌ स्पीच समझ नहीं आया: {e}")
        
# Show extracted data if exists
if "extracted_data" in st.session_state:
    st.json(st.session_state["extracted_data"])
    if st.button("✅ Save this!!"):
        send_to_firebase(st.session_state["extracted_data"])
        st.success("✅ डेटा सेव हो गया!")
        del st.session_state["extracted_data"]  # Clear after saving


st.markdown("---")
st.subheader("🔍 Find Customer Record ")
search_name = st.text_input("ग्राहक का नाम टाइप करें:")
if st.button("🔎 खोजें") and search_name.strip():
    result = get_customer_udhaar(search_name.strip())
    if not result['udhar_records'] and not result['paid_records']:
        st.warning(f"'{search_name}' का कोई रिकॉर्ड नहीं मिला।")
    else:
        st.markdown(f"### 💰 {search_name} का कुल उधार: ₹{result['udhar_total']}")
        if result['udhar_records']:
            st.markdown("**उधार Transactions:**")
            for r in result['udhar_records']:
                st.markdown(f"- ₹{r['amount']}: {r['item']} ({r['date']})")

        st.markdown(f"### 🧾 अब तक चुकाया: ₹{result['paid_total']}")
        if result['paid_records']:
            st.markdown("**चुकाया Transactions:**")
            for r in result['paid_records']:
                st.markdown(f"- ₹{r['amount']}: {r['item']} ({r['date']})")

        st.markdown(f"### 💼 वर्तमान बकाया: ₹{result['net_balance']}")

st.markdown("---")
st.subheader("✍️ Manual Entry")
with st.form("manual_form"):
    name = st.text_input("Name")
    amount = st.number_input("Amount (₹)", min_value=1, step=1)
    item = st.text_input("Item")
    type = st.selectbox("Type", ["Udhar", "Paid", "Nagat"])
    date = st.date_input("Date", value=datetime.today())
    submit_btn = st.form_submit_button("Save this!!")

    if submit_btn:
        manual_data = {
            "customer_name": name,
            "item": item,
            "amount": amount,
            "type": type,
            "date": date.strftime("%Y-%m-%d")
        }
        send_to_firebase(manual_data)
        st.success("✅ Manual Data is Saved")


# VISUALIZATION

import pandas as pd
import plotly.express as px

# --- Fetch all data for visualization ---
def fetch_all_transactions():
    ref = db.reference("transactions")
    all_data = ref.get()
    if not all_data:
        return pd.DataFrame()
    df = pd.DataFrame(all_data.values())
    
    # Normalize columns
    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0).astype(int)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if "customer_name" not in df.columns and "name" in df.columns:
        df["customer_name"] = df["name"]  # sometimes your data uses 'name'
    
    return df


st.markdown("---")
st.subheader("📊 Udhaar Visualization Dashboard")

if st.button("📊 Show Bar Chart: Total Udhaar per Customer"):
    df = fetch_all_transactions()
    if df.empty:
        st.warning("⚠️ अभी तक कोई डेटा सेव नहीं हुआ।")
    else:
        # Group by customer
        df_grouped = df[df["type"] == "Udhar"].groupby("customer_name")["amount"].sum().reset_index()
        fig = px.bar(df_grouped,
                     x="customer_name", y="amount",
                     text="amount",
                     title="💰 Total Udhaar Amount per Customer",
                     labels={"customer_name": "Customer Name", "amount": "Udhar Amount"})
        fig.update_traces(marker_color="indianred", textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

if st.button("📈 Show Line Chart: Udhaar Over Time"):
    df = fetch_all_transactions()
    if df.empty:
        st.warning("⚠️ अभी तक कोई डेटा सेव नहीं हुआ।")
    else:
        df_grouped = df[df["type"] == "Udhar"].groupby("date")["amount"].sum().reset_index()
        fig = px.line(df_grouped,
                      x="date", y="amount",
                      markers=True,
                      title="📆 Udhaar Over Time",
                      labels={"date": "Date", "amount": "Total Udhar"})
        fig.update_traces(line=dict(color="green", width=3))
        st.plotly_chart(fig, use_container_width=True)


import streamlit as st
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase
import av
import speech_recognition as sr
import asyncio
import threading
from datetime import datetime
import unicodedata
import re
import firebase_admin
from firebase_admin import credentials, db

# Initialize Firebase only once
if not firebase_admin._apps:
    cred = credentials.Certificate("D:\\Udhar_System\\udhar-system-be29b-firebase-adminsdk-fbsvc-0768802c39.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://udhar-system-be29b-default-rtdb.firebaseio.com/'
    })

# Firebase functions
def send_to_firebase(data):
    ref = db.reference("transactions")
    ref.push(data)

def get_customer_udhaar(name):
    name = unicodedata.normalize('NFC', name.strip())
    ref = db.reference('transactions')
    all_data = ref.get()

    udhar_total = 0
    paid_total = 0
    udhar_records = []
    paid_records = []

    if all_data:
        for key, record in all_data.items():
            rec_name = unicodedata.normalize('NFC', record.get('name', '').strip())
            if rec_name == name:
                if record.get('type') == 'Udhar':
                    udhar_records.append(record)
                    udhar_total += int(record.get('amount', 0))
                elif record.get('type') == 'Paid':
                    paid_records.append(record)
                    paid_total += int(record.get('amount', 0))

    return {
        'udhar_records': udhar_records,
        'paid_records': paid_records,
        'net_balance': udhar_total - paid_total,
        'udhar_total': udhar_total,
        'paid_total': paid_total
    }

import speech_recognition as sr

def get_voice_text(timeout=6, lang='hi-IN'):
    r = sr.Recognizer()
    with sr.Microphone() as source:
        audio = r.listen(source, timeout=timeout)
    text = r.recognize_google(audio, language=lang)
    return text


# Extract info from speech
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




# Streamlit GUI
st.set_page_config(page_title="📒 SmartKhata", layout="centered")
st.title("🗣️ SmartKhata System")

# Voice input and confirmation
if st.button("🎙️ बोलकर एंट्री करें"):
    with st.spinner("कृपया बोलें..."):
        try:
            text = get_voice_text()
            extracted = extract_info(text)
            st.session_state["extracted_data"] = extracted  # Save in session state
            st.success("📢 आपने कहा:")
        except Exception as e:
            st.error(f"❌ स्पीच समझ नहीं आया: {e}")
        # r = sr.Recognizer()
        # with sr.Microphone() as source:
        #     audio = r.listen(source, timeout=6)
        # try:
        #     text = r.recognize_google(audio, language='hi-IN')
        #     extracted = extract_info(text)
        #     st.session_state["extracted_data"] = extracted  # Save in session state
        #     st.success("📢 आपने कहा:")
        # except Exception as e:
        #     st.error(f"❌ स्पीच समझ नहीं आया: {e}")

# Show extracted data if exists
if "extracted_data" in st.session_state:
    st.json(st.session_state["extracted_data"])
    if st.button("✅ यह सही है, सेव करें"):
        send_to_firebase(st.session_state["extracted_data"])
        st.success("✅ डेटा सेव हो गया!")
        del st.session_state["extracted_data"]  # Clear after saving


st.markdown("---")
st.subheader("🔍 ग्राहक का रिकॉर्ड खोजें")
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
st.subheader("✍️ मैन्युअल एंट्री")
with st.form("manual_form"):
    name = st.text_input("नाम")
    amount = st.number_input("राशि (₹)", min_value=1, step=1)
    item = st.text_input("आइटम")
    type = st.selectbox("टाइप", ["Udhar", "Paid", "Nagat"])
    date = st.date_input("तारीख", value=datetime.today())
    submit_btn = st.form_submit_button("सेव करें")

    if submit_btn:
        manual_data = {
            "name": name,
            "amount": amount,
            "item": item,
            "type": type,
            "date": date.strftime("%Y-%m-%d %H:%M:%S")
        }
        send_to_firebase(manual_data)
        st.success("✅ मैन्युअल डेटा सेव हो गया!")

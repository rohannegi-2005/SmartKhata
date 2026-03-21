import streamlit as st
import os
import plotly.express as px
import io
import speech_recognition as sr          # moved to top — fixes scoping bug on line 83
from pydub import AudioSegment           # moved to top — consistent with other imports

from infrastructure.groq_extractor import GroqExtractor
from infrastructure.firebase_repo import FirebaseRepository
from infrastructure.pdf_generator import generate_ledger_pdf  # moved to top
from services.transaction_service import TransactionService
from domain.transaction import Transaction


# ── Config ────────────────────────────────────────────────────────────────────
def get_config():
    try:
        api_key        = st.secrets["GROQ_API_KEY"]
        firebase_creds = dict(st.secrets["firebase"])
        return api_key, firebase_creds
    except Exception:
        from dotenv import load_dotenv
        load_dotenv()
        api_key        = os.getenv("GROQ_API_KEY")
        firebase_creds = os.getenv("FIREBASE_JSON_PATH")
        if not api_key:
            st.error("GROQ_API_KEY not found in secrets or .env — app cannot start.")
            st.stop()
        return api_key, firebase_creds

API_KEY, DB_CREDS = get_config()
DB_URL = "https://udhar-system-be29b-default-rtdb.firebaseio.com/"

extractor       = GroqExtractor(API_KEY)
repo            = FirebaseRepository(DB_CREDS, DB_URL)
transaction_svc = TransactionService(repo)


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="SmartKhata Pro", layout="centered")
st.title("SmartKhata System")


# ── 1. Voice Entry ────────────────────────────────────────────────────────────
st.subheader("Voice Entry")
st.info("Allow mic access → Click mic → Speak → Click Stop")

audio_input = st.audio_input("Record Udhaar transaction (Hindi or English)")

if audio_input is not None:
    with st.spinner("Processing voice..."):
        try:
            # Convert browser audio (WebM/OGG) → WAV
            raw     = io.BytesIO(audio_input.read())
            segment = AudioSegment.from_file(raw)
            wav_io  = io.BytesIO()
            segment.export(wav_io, format="wav")
            wav_io.seek(0)

            recognizer = sr.Recognizer()
            with sr.AudioFile(wav_io) as source:
                audio_data = recognizer.record(source)

            # Try Hindi first, fallback to English
            try:
                text = recognizer.recognize_google(audio_data, language="hi-IN")
            except sr.UnknownValueError:
                text = recognizer.recognize_google(audio_data, language="en-IN")

            st.success(f"Recognized: **{text}**")

            # extractor.extract() returns a dict — wrap into Transaction object
            data = extractor.extract(text)
            txn  = Transaction(
                customer_name = data.get("customer_name", "Unknown"),
                amount        = data.get("amount", 0),
                item          = data.get("item", ""),
                t_type        = data.get("type", "Nagat"),
                date          = data.get("date")
            )
            st.session_state["pending_txn"] = txn
            st.info(f"Name: {txn.customer_name} | Amount: Rs.{txn.amount} | Item: {txn.item} | Type: {txn.type}")

        except sr.UnknownValueError:
            st.error("Could not understand. Please speak clearly and try again.")
        except Exception as e:
            st.error(f"Voice error: {e}")

if "pending_txn" in st.session_state:
    txn = st.session_state["pending_txn"]
    st.json(txn.to_dict())
    if st.button("Save Voice Transaction"):
        transaction_svc.save_transaction(txn)
        st.success("Saved!")
        del st.session_state["pending_txn"]

st.markdown("---")


# ── 2. Search ─────────────────────────────────────────────────────────────────
st.subheader("Find Customer Record")
search_name = st.text_input("Enter Customer Name:")
if st.button("Search") and search_name:
    result = transaction_svc.get_ledger_for_customer(search_name)
    if not result or (not result["udhar_records"] and not result["paid_records"]):
        st.warning("No records found.")
    else:
        st.markdown(f"### Net Balance: Rs.{result['net_balance']}")
        c1, c2 = st.columns(2)
        with c1:
            st.error(f"Total Udhar: Rs.{result['udhar_total']}")
            for r in result["udhar_records"]:
                st.write(f"- Rs.{r['amount']} ({r.get('item', '')})")
        with c2:
            st.success(f"Total Paid: Rs.{result['paid_total']}")
            for r in result["paid_records"]:
                st.write(f"- Rs.{r['amount']} ({r.get('item', '')})")

        st.markdown("---")
        try:
            pdf_bytes = generate_ledger_pdf(search_name, result)
            st.download_button(
                label="Download PDF Statement",
                data=pdf_bytes,
                file_name=f"SmartKhata_{search_name.replace(' ', '_')}.pdf",
                mime="application/pdf",
                help="Download a clean PDF statement for this customer"
            )
        except Exception as e:
            st.warning(f"PDF export unavailable: {e}")

st.markdown("---")


# ── 3. Manual Entry ───────────────────────────────────────────────────────────
st.subheader("Manual Entry")
with st.form("manual_form"):
    name   = st.text_input("Customer Name")
    amount = st.number_input("Amount (Rs.)", min_value=1)
    item   = st.text_input("Item")
    t_type = st.selectbox("Type", ["Udhar", "Paid", "Nagat"])
    if st.form_submit_button("Save"):
        if name.strip():
            transaction_svc.save_transaction(Transaction(name, amount, item, t_type))
            st.success("Saved!")
        else:
            st.warning("Please enter a customer name.")

st.markdown("---")


# ── 4. Analytics ──────────────────────────────────────────────────────────────
st.subheader("Analytics Dashboard")
if st.button("Show Charts"):
    df = transaction_svc.get_analytics_dataframe()
    if not df.empty and "type" in df.columns:
        udhar_df = df[df["type"] == "Udhar"].copy()
        if not udhar_df.empty:
            bar = udhar_df.groupby("customer_name")["amount"].sum().reset_index()
            st.plotly_chart(
                px.bar(bar, x="customer_name", y="amount",
                       title="Total Udhar per Customer",
                       color="amount", color_continuous_scale="reds"),
                use_container_width=True
            )
            if "date" in udhar_df.columns:
                udhar_df["day"] = udhar_df["date"].dt.date
                line = udhar_df.groupby("day")["amount"].sum().reset_index()
                st.plotly_chart(
                    px.line(line, x="day", y="amount",
                            title="Udhar Trend Over Time", markers=True),
                    use_container_width=True
                )
        else:
            st.info("No Udhar records to visualize yet.")
    else:
        st.warning("No data available.")
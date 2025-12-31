import streamlit as st
import os
import plotly.express as px
from datetime import datetime
from dotenv import load_dotenv

# Import our new modules
from infrastructure.speech_engine import SpeechEngine
from infrastructure.groq_extractor import GroqExtractor
from infrastructure.firebase_repo import FirebaseRepository
from services.voice_service import VoiceService
from services.transaction_service import TransactionService
from domain.transaction import Transaction

# Load Config
load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY")
DB_KEY_PATH = os.getenv("FIREBASE_JSON_PATH")
DB_URL = "https://udhar-system-be29b-default-rtdb.firebaseio.com/" # Replace if needed

# --- Dependency Injection (Wiring the system) ---
speech = SpeechEngine()
extractor = GroqExtractor(API_KEY)
repo = FirebaseRepository(DB_KEY_PATH, DB_URL)

voice_service = VoiceService(speech, extractor)
transaction_service = TransactionService(repo)

# --- UI Layout ---
st.set_page_config(page_title="📒 SmartKhata Pro", layout="centered")
st.title("🗣️ SmartKhata System (OOP)")

# 1. Voice Section
if st.button("🎙️ Speak"):
    with st.spinner("Listening..."):
        try:
            # The Service handles Listen -> Extract -> Object Creation
            txn = voice_service.process_voice_command()
            
            # Store in session state to review before saving
            st.session_state["pending_txn"] = txn
            st.success(f"Recognized: {txn.customer_name} | ₹{txn.amount}")
        except Exception as e:
            st.error(f"Error: {e}")

if "pending_txn" in st.session_state:
    txn = st.session_state["pending_txn"]
    st.json(txn.to_dict())
    
    if st.button("✅ Save Voice Transaction"):
        transaction_service.save_transaction(txn)
        st.success("Saved!")
        del st.session_state["pending_txn"]

st.markdown("---")

# 2. Search Section
st.subheader("🔍 Find Customer Record")
search_name = st.text_input("Enter Name:")
if st.button("🔎 Search") and search_name:
    result = transaction_service.get_ledger_for_customer(search_name)
    
    if not result or (not result['udhar_records'] and not result['paid_records']):
        st.warning("No records found.")
    else:
        st.markdown(f"### Net Balance: ₹{result['net_balance']}")
        
        c1, c2 = st.columns(2)
        with c1:
            st.error(f"Total Udhar: ₹{result['udhar_total']}")
            for r in result['udhar_records']:
                st.write(f"- ₹{r['amount']} ({r['item']})")
        with c2:
            st.success(f"Total Paid: ₹{result['paid_total']}")
            for r in result['paid_records']:
                st.write(f"- ₹{r['amount']} ({r['item']})")

st.markdown("---")

# 3. Manual Entry Section
st.subheader("✍️ Manual Entry")
with st.form("manual_form"):
    name = st.text_input("Name")
    amount = st.number_input("Amount", min_value=1)
    item = st.text_input("Item")
    t_type = st.selectbox("Type", ["Udhar", "Paid", "Nagat"])
    submit = st.form_submit_button("Save Manual")
    
    if submit:
        manual_txn = Transaction(name, amount, item, t_type)
        transaction_service.save_transaction(manual_txn)
        st.success("Manual Entry Saved!")

st.markdown("---")

# 4. Visualization Section
st.subheader("📊 Analytics")
if st.button("Show Charts"):
    df = transaction_service.get_analytics_dataframe()
    if not df.empty:
        # Bar Chart
        df_grouped = df[df["type"] == "Udhar"].groupby("customer_name")["amount"].sum().reset_index()
        fig_bar = px.bar(df_grouped, x="customer_name", y="amount", title="Total Udhar per Customer")
        st.plotly_chart(fig_bar)
        
        # Line Chart
        df_time = df[df["type"] == "Udhar"].groupby("date")["amount"].sum().reset_index()
        fig_line = px.line(df_time, x="date", y="amount", title="Udhar Trend Over Time")
        st.plotly_chart(fig_line)
    else:
        st.warning("No data to visualize.")
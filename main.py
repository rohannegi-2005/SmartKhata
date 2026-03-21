import streamlit as st
import os
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import io
from datetime import datetime, timedelta, date
import speech_recognition as sr
from pydub import AudioSegment

from infrastructure.groq_extractor import GroqExtractor
from infrastructure.firebase_repo import FirebaseRepository
from infrastructure.pdf_generator import generate_ledger_pdf
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


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def get_filtered_data(df: pd.DataFrame,
                      start: date, end: date,
                      customer: str = "All") -> pd.DataFrame:
    """Filter dataframe by date range and optional customer."""
    if df.empty:
        return df
    filtered = df.copy()
    if "date" in filtered.columns:
        filtered = filtered[
            (filtered["date"].dt.date >= start) &
            (filtered["date"].dt.date <= end)
        ]
    if customer != "All" and "customer_name" in filtered.columns:
        filtered = filtered[filtered["customer_name"] == customer]
    return filtered


def compute_metrics(df: pd.DataFrame) -> dict:
    """Compute summary KPIs from filtered dataframe."""
    if df.empty:
        return {"udhar": 0, "paid": 0, "net": 0, "customers": 0}

    udhar = int(df[df["type"] == "Udhar"]["amount"].sum()) if "type" in df.columns else 0
    paid  = int(df[df["type"] == "Paid"]["amount"].sum())  if "type" in df.columns else 0
    customers = df["customer_name"].nunique() if "customer_name" in df.columns else 0

    return {
        "udhar":     udhar,
        "paid":      paid,
        "net":       udhar - paid,
        "customers": customers,
    }


def build_top_debtors_chart(df: pd.DataFrame) -> go.Figure | None:
    """Bar chart — top 5 customers by outstanding Udhar."""
    udhar_df = df[df["type"] == "Udhar"] if "type" in df.columns else pd.DataFrame()
    paid_df  = df[df["type"] == "Paid"]  if "type" in df.columns else pd.DataFrame()

    if udhar_df.empty:
        return None

    udhar_sum = udhar_df.groupby("customer_name")["amount"].sum()
    paid_sum  = paid_df.groupby("customer_name")["amount"].sum() if not paid_df.empty else pd.Series(dtype=int)
    net       = (udhar_sum - paid_sum.reindex(udhar_sum.index, fill_value=0)).sort_values(ascending=False).head(5)
    net       = net[net > 0].reset_index()
    net.columns = ["customer_name", "net_udhar"]

    if net.empty:
        return None

    fig = px.bar(
        net, x="customer_name", y="net_udhar",
        title="Top 5 Debtors (Net Outstanding)",
        labels={"customer_name": "Customer", "net_udhar": "Rs."},
        color="net_udhar", color_continuous_scale="reds",
        text="net_udhar",
    )
    fig.update_traces(texttemplate="Rs. %{text}", textposition="outside")
    fig.update_layout(
        showlegend=False, coloraxis_showscale=False,
        margin=dict(t=40, b=20, l=10, r=10),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#e0e0e0"),
    )
    return fig


def build_trend_chart(df: pd.DataFrame) -> go.Figure | None:
    """Line chart — daily Udhar amount over the selected period."""
    udhar_df = df[df["type"] == "Udhar"].copy() if "type" in df.columns else pd.DataFrame()
    if udhar_df.empty or "date" not in udhar_df.columns:
        return None

    udhar_df["day"] = udhar_df["date"].dt.date
    trend = udhar_df.groupby("day")["amount"].sum().reset_index()
    trend.columns = ["day", "amount"]

    fig = px.line(
        trend, x="day", y="amount",
        title="Daily Udhar Trend",
        labels={"day": "Date", "amount": "Rs."},
        markers=True,
    )
    fig.update_traces(line_color="#e53935", marker_color="#e53935")
    fig.update_layout(
        margin=dict(t=40, b=20, l=10, r=10),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#e0e0e0"),
    )
    return fig


def build_volume_chart(df: pd.DataFrame) -> go.Figure | None:
    """Bar chart — daily transaction count (all types)."""
    if df.empty or "date" not in df.columns:
        return None

    df = df.copy()
    df["day"] = df["date"].dt.date
    vol = df.groupby("day").size().reset_index(name="count")

    fig = px.bar(
        vol, x="day", y="count",
        title="Daily Transaction Volume",
        labels={"day": "Date", "count": "Transactions"},
        color_discrete_sequence=["#1565c0"],
    )
    fig.update_layout(
        margin=dict(t=40, b=20, l=10, r=10),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#e0e0e0"),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# PAGE
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="SmartKhata Pro", layout="wide")
st.title("SmartKhata")

tab_dashboard, tab_ledger = st.tabs(["Dashboard", "Ledger"])


# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — DASHBOARD
# ═════════════════════════════════════════════════════════════════════════════
with tab_dashboard:

    # ── Fetch data once ───────────────────────────────────────────────────────
    raw_df = transaction_svc.get_analytics_dataframe()

    if raw_df.empty:
        st.info("No transactions yet. Add entries in the Ledger tab to see analytics.")
        st.stop()

    # ── Filters ───────────────────────────────────────────────────────────────
    col_f1, col_f2, col_f3 = st.columns([2, 2, 2])

    with col_f1:
        date_range = st.date_input(
            "Date range",
            value=(date.today() - timedelta(days=30), date.today()),
            max_value=date.today(),
        )

    with col_f2:
        customers = ["All"] + sorted(
            raw_df["customer_name"].dropna().unique().tolist()
        ) if "customer_name" in raw_df.columns else ["All"]
        selected_customer = st.selectbox("Customer", customers)

    # Unpack date range safely (user might pick only one date)
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = end_date = date_range if not isinstance(date_range, (list, tuple)) else date_range[0]

    df = get_filtered_data(raw_df, start_date, end_date, selected_customer)
    metrics = compute_metrics(df)

    st.markdown("")

    # ── KPI metrics row ───────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)

    # Compute deltas vs previous period of same length for context
    period_days = max((end_date - start_date).days, 1)
    prev_start  = start_date - timedelta(days=period_days)
    prev_df     = get_filtered_data(raw_df, prev_start, start_date - timedelta(days=1), selected_customer)
    prev_m      = compute_metrics(prev_df)

    m1.metric(
        "Total Udhar",
        f"Rs. {metrics['udhar']:,}",
        delta=f"Rs. {metrics['udhar'] - prev_m['udhar']:+,} vs prev period",
        delta_color="inverse",
    )
    m2.metric(
        "Total Paid",
        f"Rs. {metrics['paid']:,}",
        delta=f"Rs. {metrics['paid'] - prev_m['paid']:+,} vs prev period",
    )
    m3.metric(
        "Net Balance",
        f"Rs. {metrics['net']:,}",
        delta=f"Rs. {metrics['net'] - prev_m['net']:+,} vs prev period",
        delta_color="inverse",
    )
    m4.metric(
        "Active Customers",
        metrics["customers"],
        delta=f"{metrics['customers'] - prev_m['customers']:+d} vs prev period",
    )

    st.markdown("---")

    # ── Charts row 1: top debtors + trend ─────────────────────────────────────
    ch1, ch2 = st.columns(2)

    with ch1:
        fig_debtors = build_top_debtors_chart(df)
        if fig_debtors:
            st.plotly_chart(fig_debtors, use_container_width=True)
        else:
            st.info("No outstanding Udhar in this period.")

    with ch2:
        fig_trend = build_trend_chart(df)
        if fig_trend:
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("No Udhar transactions in this period.")

    # ── Charts row 2: transaction volume ──────────────────────────────────────
    fig_vol = build_volume_chart(df)
    if fig_vol:
        st.plotly_chart(fig_vol, use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — LEDGER (all existing features)
# ═════════════════════════════════════════════════════════════════════════════
with tab_ledger:

    # ── Voice Entry ───────────────────────────────────────────────────────────
    st.subheader("Voice Entry")
    st.info("Allow mic access → Click mic → Speak → Click Stop")

    audio_input = st.audio_input("Record Udhaar transaction (Hindi or English)")

    if audio_input is not None:
        with st.spinner("Processing voice..."):
            try:
                raw     = io.BytesIO(audio_input.read())
                segment = AudioSegment.from_file(raw)
                wav_io  = io.BytesIO()
                segment.export(wav_io, format="wav")
                wav_io.seek(0)

                recognizer = sr.Recognizer()
                with sr.AudioFile(wav_io) as source:
                    audio_data = recognizer.record(source)

                try:
                    text = recognizer.recognize_google(audio_data, language="hi-IN")
                except sr.UnknownValueError:
                    text = recognizer.recognize_google(audio_data, language="en-IN")

                st.success(f"Recognized: **{text}**")

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

    # ── Search + PDF ──────────────────────────────────────────────────────────
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

    # ── Manual Entry ──────────────────────────────────────────────────────────
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
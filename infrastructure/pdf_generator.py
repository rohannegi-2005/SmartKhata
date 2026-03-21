import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT


# ── Colour palette ────────────────────────────────────────────────────────────
DARK       = colors.HexColor("#1a1a2e")
ACCENT     = colors.HexColor("#16213e")
GREEN      = colors.HexColor("#0f9b58")
GREEN_LIGHT= colors.HexColor("#e8f5e9")
RED        = colors.HexColor("#c62828")
RED_LIGHT  = colors.HexColor("#ffebee")
BLUE       = colors.HexColor("#1565c0")
BLUE_LIGHT = colors.HexColor("#e3f2fd")
GRAY_LIGHT = colors.HexColor("#f5f5f5")
GRAY_MID   = colors.HexColor("#e0e0e0")
GRAY_TEXT  = colors.HexColor("#757575")
WHITE      = colors.white
BLACK      = colors.HexColor("#212121")


def generate_ledger_pdf(customer_name: str, ledger: dict) -> bytes:
    """
    Generate a professional A4 PDF ledger statement.

    Args:
        customer_name: Name of the customer
        ledger: dict with keys:
                  udhar_records  → list of dicts {amount, item, date, ...}
                  paid_records   → list of dicts {amount, item, date, ...}
                  udhar_total    → int
                  paid_total     → int
                  net_balance    → int

    Returns:
        PDF as bytes (ready for st.download_button)
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    W = A4[0] - 40 * mm          # usable width
    story = []

    # ── 1. Header band ────────────────────────────────────────────────────────
    header_data = [[
        Paragraph(
            '<font color="white" size="18"><b>SmartKhata</b></font><br/>'
            '<font color="#aaaacc" size="9">Voice-Powered Udhaar Management</font>',
            ParagraphStyle("hdr", alignment=TA_LEFT)
        ),
        Paragraph(
            '<font color="white" size="9">Customer Statement</font><br/>'
            f'<font color="#aaaacc" size="8">Generated: {datetime.now().strftime("%d %b %Y, %I:%M %p")}</font>',
            ParagraphStyle("hdr_r", alignment=TA_RIGHT)
        ),
    ]]
    header_table = Table(header_data, colWidths=[W * 0.55, W * 0.45])
    header_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), DARK),
        ("ROWPADDING",  (0, 0), (-1, -1), 10),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("ROUNDEDCORNERS", [6]),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 6 * mm))

    # ── 2. Customer info card ─────────────────────────────────────────────────
    info_data = [[
        Paragraph(
            f'<font size="13"><b>{customer_name}</b></font><br/>'
            f'<font color="#888888" size="8">Statement Period: All Transactions</font>',
            ParagraphStyle("info", alignment=TA_LEFT)
        ),
        Paragraph(
            f'<font size="8" color="#888888">Account Type</font><br/>'
            f'<font size="10"><b>Udhaar Ledger</b></font>',
            ParagraphStyle("info_c", alignment=TA_CENTER)
        ),
        Paragraph(
            f'<font size="8" color="#888888">Net Balance</font><br/>'
            + (
                f'<font size="13" color="#c62828"><b>Rs. {ledger["net_balance"]}</b></font>'
                if ledger["net_balance"] > 0
                else f'<font size="13" color="#0f9b58"><b>Rs. {abs(ledger["net_balance"])}</b></font>'
            )
            + '<br/>'
            + (
                '<font size="8" color="#c62828">Amount Owed</font>'
                if ledger["net_balance"] > 0
                else '<font size="8" color="#0f9b58">Credit / Advance</font>'
            ),
            ParagraphStyle("info_r", alignment=TA_RIGHT)
        ),
    ]]
    info_table = Table(info_data, colWidths=[W * 0.45, W * 0.25, W * 0.30])
    info_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), GRAY_LIGHT),
        ("BOX",         (0, 0), (-1, -1), 0.5, GRAY_MID),
        ("ROWPADDING",  (0, 0), (-1, -1), 10),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("LINEAFTER",   (0, 0), (1, -1),  0.5, GRAY_MID),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 6 * mm))

    # ── 3. Summary KPI row ────────────────────────────────────────────────────
    def kpi_cell(label, value, bg, text_color):
        return Paragraph(
            f'<font size="8" color="#888888">{label}</font><br/>'
            f'<font size="14" color="{text_color}"><b>Rs. {value}</b></font>',
            ParagraphStyle("kpi", alignment=TA_CENTER)
        )

    kpi_data = [[
        kpi_cell("Total Udhar",   ledger["udhar_total"], RED_LIGHT,  "#c62828"),
        kpi_cell("Total Paid",    ledger["paid_total"],  GREEN_LIGHT, "#0f9b58"),
        kpi_cell("Net Balance",   ledger["net_balance"], BLUE_LIGHT,  "#1565c0"),
        Paragraph(
            f'<font size="8" color="#888888">Transactions</font><br/>'
            f'<font size="14" color="#424242"><b>'
            f'{len(ledger["udhar_records"]) + len(ledger["paid_records"])}'
            f'</b></font>',
            ParagraphStyle("kpi_c", alignment=TA_CENTER)
        ),
    ]]
    kpi_table = Table(kpi_data, colWidths=[W / 4] * 4)
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (0, -1), RED_LIGHT),
        ("BACKGROUND",  (1, 0), (1, -1), GREEN_LIGHT),
        ("BACKGROUND",  (2, 0), (2, -1), BLUE_LIGHT),
        ("BACKGROUND",  (3, 0), (3, -1), GRAY_LIGHT),
        ("BOX",         (0, 0), (-1, -1), 0.5, GRAY_MID),
        ("LINEAFTER",   (0, 0), (2, -1),  0.5, GRAY_MID),
        ("ROWPADDING",  (0, 0), (-1, -1), 10),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 7 * mm))

    # ── 4. Transaction table helper ───────────────────────────────────────────
    def build_tx_table(records, label, header_bg, amount_color, amount_bg):
        story.append(Paragraph(
            f'<font size="11" color="{DARK.hexval() if False else "#1a1a2e"}"><b>{label}</b></font>'
            f'  <font size="8" color="#888888">({len(records)} entries)</font>',
            ParagraphStyle("sec_hdr", alignment=TA_LEFT)
        ))
        story.append(Spacer(1, 2 * mm))

        if not records:
            story.append(Paragraph(
                '<font color="#aaaaaa" size="9">No records found.</font>',
                ParagraphStyle("empty", alignment=TA_LEFT, leftIndent=4)
            ))
            story.append(Spacer(1, 4 * mm))
            return

        # Table header
        col_headers = [
            Paragraph('<b><font size="9" color="white">Date &amp; Time</font></b>',
                      ParagraphStyle("th", alignment=TA_LEFT)),
            Paragraph('<b><font size="9" color="white">Item / Description</font></b>',
                      ParagraphStyle("th", alignment=TA_LEFT)),
            Paragraph('<b><font size="9" color="white">Amount</font></b>',
                      ParagraphStyle("th_r", alignment=TA_RIGHT)),
        ]

        rows = [col_headers]
        for i, rec in enumerate(records):
            raw_date = rec.get("date", "")
            try:
                dt = datetime.strptime(raw_date, "%Y-%m-%d %H:%M:%S")
                date_str = dt.strftime("%d %b %Y")
                time_str = dt.strftime("%I:%M %p")
            except Exception:
                date_str = raw_date
                time_str = ""

            row_bg = WHITE if i % 2 == 0 else GRAY_LIGHT

            rows.append([
                Paragraph(
                    f'<font size="9">{date_str}</font><br/>'
                    f'<font size="7" color="#888888">{time_str}</font>',
                    ParagraphStyle("td", alignment=TA_LEFT)
                ),
                Paragraph(
                    f'<font size="9">{rec.get("item", "—")}</font>',
                    ParagraphStyle("td", alignment=TA_LEFT)
                ),
                Paragraph(
                    f'<font size="10" color="{amount_color}"><b>Rs. {rec.get("amount", 0)}</b></font>',
                    ParagraphStyle("td_r", alignment=TA_RIGHT)
                ),
            ])

        # Total row
        rows.append([
            Paragraph("", ParagraphStyle("x")),
            Paragraph('<b><font size="9">Total</font></b>',
                      ParagraphStyle("tot_l", alignment=TA_RIGHT)),
            Paragraph(
                f'<b><font size="10" color="{amount_color}">'
                f'Rs. {sum(r.get("amount", 0) for r in records)}'
                f'</font></b>',
                ParagraphStyle("tot_r", alignment=TA_RIGHT)
            ),
        ])

        tx_table = Table(rows, colWidths=[W * 0.28, W * 0.48, W * 0.24])
        style = TableStyle([
            # Header row
            ("BACKGROUND",   (0, 0), (-1, 0),  header_bg),
            ("ROWPADDING",   (0, 0), (-1, -1), 7),
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
            ("BOX",          (0, 0), (-1, -1), 0.5, GRAY_MID),
            ("LINEBELOW",    (0, 0), (-1, 0),   0.5, GRAY_MID),
            # Total row
            ("BACKGROUND",   (0, -1), (-1, -1), amount_bg),
            ("LINEABOVE",    (0, -1), (-1, -1), 0.5, GRAY_MID),
        ])
        # Alternating row colours (skip header row 0 and total row -1)
        for i in range(1, len(rows) - 1):
            bg = WHITE if i % 2 == 1 else GRAY_LIGHT
            style.add("BACKGROUND", (0, i), (-1, i), bg)

        tx_table.setStyle(style)
        story.append(tx_table)
        story.append(Spacer(1, 6 * mm))

    build_tx_table(
        ledger["udhar_records"], "Udhar (Credit Given)",
        header_bg=RED, amount_color="#c62828", amount_bg=RED_LIGHT
    )
    build_tx_table(
        ledger["paid_records"], "Paid (Amount Recovered)",
        header_bg=GREEN, amount_color="#0f9b58", amount_bg=GREEN_LIGHT
    )

    # ── 5. Footer ─────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_MID))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        '<font size="7" color="#aaaaaa">'
        'Generated by SmartKhata — Voice &amp; AI-Powered Udhaar Management  |  '
        'This is a system-generated statement and does not require a signature.'
        '</font>',
        ParagraphStyle("footer", alignment=TA_CENTER)
    ))

    doc.build(story)
    return buffer.getvalue()

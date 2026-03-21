import io
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ── Register Unicode fonts (Devanagari / Hindi support) ───────────────────────
def _register_fonts():
    """
    Register fonts that support Devanagari script.
    Priority:
      1. Noto Sans Devanagari (bundled in assets/ if present)
      2. FreeSans (ships with Ubuntu/Debian — used on Streamlit Cloud)
      3. Fallback to Helvetica (English only — black boxes for Hindi)
    """
    # Option 1: Noto Sans Devanagari bundled in project assets/
    base_dir   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    noto_reg   = os.path.join(base_dir, "assets", "NotoSans-Regular.ttf")
    noto_bold  = os.path.join(base_dir, "assets", "NotoSans-Bold.ttf")
    if os.path.exists(noto_reg):
        pdfmetrics.registerFont(TTFont("Hindi",     noto_reg))
        pdfmetrics.registerFont(TTFont("HindiBold", noto_bold if os.path.exists(noto_bold) else noto_reg))
        return "Hindi", "HindiBold"

    # Option 2: FreeSans — present on Streamlit Cloud (Ubuntu/Debian)
    free_reg  = "/usr/share/fonts/truetype/freefont/FreeSans.ttf"
    free_bold = "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"
    if os.path.exists(free_reg):
        pdfmetrics.registerFont(TTFont("Hindi",     free_reg))
        pdfmetrics.registerFont(TTFont("HindiBold", free_bold if os.path.exists(free_bold) else free_reg))
        return "Hindi", "HindiBold"

    # Option 3: system font scan
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]:
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont("Hindi",     path))
            pdfmetrics.registerFont(TTFont("HindiBold", path))
            return "Hindi", "HindiBold"

    # Absolute fallback — no Hindi support but won't crash
    return "Helvetica", "Helvetica-Bold"


FONT_REG, FONT_BOLD = _register_fonts()


# ── Colour palette ─────────────────────────────────────────────────────────────
DARK        = colors.HexColor("#1a1a2e")
GREEN       = colors.HexColor("#0f9b58")
GREEN_LIGHT = colors.HexColor("#e8f5e9")
RED         = colors.HexColor("#c62828")
RED_LIGHT   = colors.HexColor("#ffebee")
BLUE_LIGHT  = colors.HexColor("#e3f2fd")
GRAY_LIGHT  = colors.HexColor("#f5f5f5")
GRAY_MID    = colors.HexColor("#e0e0e0")
WHITE       = colors.white


def _style(name, **kwargs):
    defaults = dict(fontName=FONT_REG, fontSize=9, leading=13)
    defaults.update(kwargs)
    return ParagraphStyle(name, **defaults)


def generate_ledger_pdf(customer_name: str, ledger: dict) -> bytes:
    """
    Generate a professional A4 PDF ledger with full Hindi/Devanagari support.

    Args:
        customer_name : customer name (Hindi or English)
        ledger        : dict with udhar_records, paid_records,
                        udhar_total, paid_total, net_balance

    Returns:
        PDF as bytes for st.download_button
    """
    buffer = io.BytesIO()
    W = A4[0] - 40 * mm

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=15*mm,  bottomMargin=15*mm,
    )
    story = []

    # ── 1. Header ─────────────────────────────────────────────────────────────
    hdr_data = [[
        Paragraph(
            f'<font color="white" size="18"><b>SmartKhata</b></font><br/>'
            f'<font color="#aaaacc" size="9">Voice-Powered Udhaar Management</font>',
            _style("h1", alignment=TA_LEFT, fontName=FONT_BOLD)
        ),
        Paragraph(
            f'<font color="white" size="9">Customer Statement</font><br/>'
            f'<font color="#aaaacc" size="8">'
            f'Generated: {datetime.now().strftime("%d %b %Y, %I:%M %p")}'
            f'</font>',
            _style("h2", alignment=TA_RIGHT)
        ),
    ]]
    hdr = Table(hdr_data, colWidths=[W*0.55, W*0.45])
    hdr.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), DARK),
        ("ROWPADDING", (0,0),(-1,-1), 10),
        ("VALIGN",     (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 5*mm))

    # ── 2. Customer info card ─────────────────────────────────────────────────
    net = ledger["net_balance"]
    net_color  = "#c62828" if net > 0 else "#0f9b58"
    net_label  = "Amount Owed" if net > 0 else "Credit / Advance"

    info_data = [[
        Paragraph(
            f'<font size="13"><b>{customer_name}</b></font><br/>'
            f'<font color="#888888" size="8">Statement Period: All Transactions</font>',
            _style("ci", alignment=TA_LEFT, fontName=FONT_BOLD)
        ),
        Paragraph(
            f'<font size="8" color="#888888">Account Type</font><br/>'
            f'<font size="10"><b>Udhaar Ledger</b></font>',
            _style("ct", alignment=TA_CENTER, fontName=FONT_BOLD)
        ),
        Paragraph(
            f'<font size="8" color="#888888">Net Balance</font><br/>'
            f'<font size="13" color="{net_color}"><b>Rs. {net}</b></font><br/>'
            f'<font size="8" color="{net_color}">{net_label}</font>',
            _style("cn", alignment=TA_RIGHT, fontName=FONT_BOLD)
        ),
    ]]
    info = Table(info_data, colWidths=[W*0.45, W*0.25, W*0.30])
    info.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), GRAY_LIGHT),
        ("BOX",        (0,0),(-1,-1), 0.5, GRAY_MID),
        ("LINEAFTER",  (0,0),(1,-1),  0.5, GRAY_MID),
        ("ROWPADDING", (0,0),(-1,-1), 10),
        ("VALIGN",     (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(info)
    story.append(Spacer(1, 5*mm))

    # ── 3. KPI summary row ────────────────────────────────────────────────────
    total_tx = len(ledger["udhar_records"]) + len(ledger["paid_records"])
    kpi_data = [[
        Paragraph(
            f'<font size="8" color="#888888">Total Udhar</font><br/>'
            f'<font size="14" color="#c62828"><b>Rs. {ledger["udhar_total"]}</b></font>',
            _style("k1", alignment=TA_CENTER, fontName=FONT_BOLD)
        ),
        Paragraph(
            f'<font size="8" color="#888888">Total Paid</font><br/>'
            f'<font size="14" color="#0f9b58"><b>Rs. {ledger["paid_total"]}</b></font>',
            _style("k2", alignment=TA_CENTER, fontName=FONT_BOLD)
        ),
        Paragraph(
            f'<font size="8" color="#888888">Net Balance</font><br/>'
            f'<font size="14" color="#1565c0"><b>Rs. {net}</b></font>',
            _style("k3", alignment=TA_CENTER, fontName=FONT_BOLD)
        ),
        Paragraph(
            f'<font size="8" color="#888888">Transactions</font><br/>'
            f'<font size="14" color="#424242"><b>{total_tx}</b></font>',
            _style("k4", alignment=TA_CENTER, fontName=FONT_BOLD)
        ),
    ]]
    kpi = Table(kpi_data, colWidths=[W/4]*4)
    kpi.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(0,-1), RED_LIGHT),
        ("BACKGROUND", (1,0),(1,-1), GREEN_LIGHT),
        ("BACKGROUND", (2,0),(2,-1), BLUE_LIGHT),
        ("BACKGROUND", (3,0),(3,-1), GRAY_LIGHT),
        ("BOX",        (0,0),(-1,-1), 0.5, GRAY_MID),
        ("LINEAFTER",  (0,0),(2,-1),  0.5, GRAY_MID),
        ("ROWPADDING", (0,0),(-1,-1), 10),
        ("VALIGN",     (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(kpi)
    story.append(Spacer(1, 6*mm))

    # ── 4. Transaction table builder ──────────────────────────────────────────
    def tx_table(records, section_label, hdr_bg, amt_color, tot_bg):
        count = len(records)
        story.append(Paragraph(
            f'<b>{section_label}</b>  '
            f'<font size="8" color="#888888">({count} entries)</font>',
            _style("sh", fontName=FONT_BOLD, fontSize=11)
        ))
        story.append(Spacer(1, 2*mm))

        if not records:
            story.append(Paragraph(
                "No records found.",
                _style("empty", textColor=colors.HexColor("#aaaaaa"))
            ))
            story.append(Spacer(1, 4*mm))
            return

        col_hdrs = [
            Paragraph("<b>Date &amp; Time</b>",    _style("th", textColor=WHITE, fontName=FONT_BOLD)),
            Paragraph("<b>Item / Description</b>", _style("th", textColor=WHITE, fontName=FONT_BOLD)),
            Paragraph("<b>Amount</b>",             _style("thr", textColor=WHITE, fontName=FONT_BOLD, alignment=TA_RIGHT)),
        ]
        rows = [col_hdrs]

        for i, rec in enumerate(records):
            raw = rec.get("date", "")
            try:
                dt       = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
                date_str = dt.strftime("%d %b %Y")
                time_str = dt.strftime("%I:%M %p")
            except Exception:
                date_str = raw
                time_str = ""

            rows.append([
                Paragraph(
                    f'{date_str}<br/>'
                    f'<font size="7" color="#888888">{time_str}</font>',
                    _style("td")
                ),
                # Item field: uses Hindi-capable font — renders Devanagari correctly
                Paragraph(
                    str(rec.get("item", "—")),
                    _style("tdi", fontName=FONT_REG)
                ),
                Paragraph(
                    f'<font color="{amt_color}"><b>Rs. {rec.get("amount", 0)}</b></font>',
                    _style("tda", alignment=TA_RIGHT, fontName=FONT_BOLD)
                ),
            ])

        total_amt = sum(r.get("amount", 0) for r in records)
        rows.append([
            Paragraph("", _style("x")),
            Paragraph("<b>Total</b>", _style("tot", alignment=TA_RIGHT, fontName=FONT_BOLD)),
            Paragraph(
                f'<font color="{amt_color}"><b>Rs. {total_amt}</b></font>',
                _style("totr", alignment=TA_RIGHT, fontName=FONT_BOLD)
            ),
        ])

        t = Table(rows, colWidths=[W*0.27, W*0.49, W*0.24])
        ts = TableStyle([
            ("BACKGROUND", (0,0),(-1,0),  hdr_bg),
            ("ROWPADDING", (0,0),(-1,-1), 7),
            ("VALIGN",     (0,0),(-1,-1), "MIDDLE"),
            ("BOX",        (0,0),(-1,-1), 0.5, GRAY_MID),
            ("LINEBELOW",  (0,0),(-1,0),  0.5, GRAY_MID),
            ("BACKGROUND", (0,-1),(-1,-1), tot_bg),
            ("LINEABOVE",  (0,-1),(-1,-1), 0.5, GRAY_MID),
        ])
        for i in range(1, len(rows)-1):
            ts.add("BACKGROUND", (0,i), (-1,i), WHITE if i%2==1 else GRAY_LIGHT)
        t.setStyle(ts)
        story.append(t)
        story.append(Spacer(1, 6*mm))

    tx_table(ledger["udhar_records"], "Udhar (Credit Given)",
             RED,   "#c62828", RED_LIGHT)
    tx_table(ledger["paid_records"],  "Paid (Amount Recovered)",
             GREEN, "#0f9b58", GREEN_LIGHT)

    # ── 5. Footer ─────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_MID))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        "Generated by SmartKhata — Voice &amp; AI-Powered Udhaar Management  |  "
        "This is a system-generated statement and does not require a signature.",
        _style("footer", alignment=TA_CENTER,
               textColor=colors.HexColor("#aaaaaa"), fontSize=7)
    ))

    doc.build(story)
    return buffer.getvalue()
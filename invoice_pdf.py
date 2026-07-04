# ==========================================================
# invoice_pdf.py
# Single/multi-page Professional Invoice Generator (No GST)
# ==========================================================

import os
from datetime import date

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ==========================================================
# PAGE SETTINGS
# ==========================================================

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN_X = 45
RIGHT_EDGE = PAGE_WIDTH - MARGIN_X


# ==========================================================
# COLOR THEME
# ==========================================================

BLUE = colors.HexColor("#123B7A")
LIGHT_BLUE = colors.HexColor("#EAF2FF")
LIGHT_GREY = colors.HexColor("#F5F7FA")
BORDER = colors.HexColor("#B8C2D1")
BLACK = colors.HexColor("#222222")
GREY = colors.HexColor("#6B7280")
WHITE = colors.white


# ==========================================================
# FONT REGISTRATION (Poppins — falls back to Helvetica if the
# font files are missing so the app never crashes)
# ==========================================================

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")

FONT_REGULAR = "Helvetica"
FONT_MEDIUM = "Helvetica"
FONT_BOLD = "Helvetica-Bold"

try:
    pdfmetrics.registerFont(TTFont("Poppins", os.path.join(FONT_DIR, "Poppins-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("Poppins-Medium", os.path.join(FONT_DIR, "Poppins-Medium.ttf")))
    pdfmetrics.registerFont(TTFont("Poppins-Bold", os.path.join(FONT_DIR, "Poppins-Bold.ttf")))
    FONT_REGULAR = "Poppins"
    FONT_MEDIUM = "Poppins-Medium"
    FONT_BOLD = "Poppins-Bold"
except Exception:
    # Fonts not found on disk -> silently keep Helvetica so PDF
    # generation never breaks.
    pass


# ==========================================================
# BASIC DRAWING HELPERS
# ==========================================================

def safe(value):
    if value is None:
        return ""
    return str(value)


def money(value):
    # Standard fonts have no Rupee glyph, so "Rs." is used instead
    # of "\u20B9" to avoid black "missing glyph" boxes.
    try:
        return f"Rs. {float(value):,.2f}"
    except Exception:
        return "Rs. 0.00"


def font_name(bold=False, medium=False):
    if bold:
        return FONT_BOLD
    if medium:
        return FONT_MEDIUM
    return FONT_REGULAR


def text(c, x, y, value, size=10, bold=False, medium=False, color=BLACK):
    c.setFillColor(color)
    c.setFont(font_name(bold, medium), size)
    c.drawString(x, y, safe(value))


def center_text(c, x, y, value, size=10, bold=False, medium=False, color=BLACK):
    c.setFillColor(color)
    c.setFont(font_name(bold, medium), size)
    c.drawCentredString(x, y, safe(value))


def right_text(c, x, y, value, size=10, bold=False, medium=False, color=BLACK):
    c.setFillColor(color)
    c.setFont(font_name(bold, medium), size)
    c.drawRightString(x, y, safe(value))


def fit_size(c, value, base_size, max_width, bold=False, min_size=6.5):
    """Shrinks the font size (never grows it) until the text fits
    inside max_width, so numbers never spill outside a table cell."""
    size = base_size
    fname = font_name(bold)
    value = safe(value)
    while size > min_size and c.stringWidth(value, fname, size) > max_width:
        size -= 0.5
    return size


def wrap_text_px(c, value, max_width, size=9, bold=False):
    """Word-wraps using real pixel width (via stringWidth) instead of
    a guessed character count, so text never overflows its column."""
    value = safe(value)
    fname = font_name(bold)
    lines, current = [], ""
    for word in value.split():
        trial = (current + " " + word).strip()
        if c.stringWidth(trial, fname, size) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            # Handle a single very long word (rare) by hard-splitting it
            while c.stringWidth(word, fname, size) > max_width and len(word) > 1:
                cut = len(word)
                while cut > 1 and c.stringWidth(word[:cut], fname, size) > max_width:
                    cut -= 1
                lines.append(word[:cut])
                word = word[cut:]
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def line(c, x1, y1, x2, y2, color=BORDER, width=1):
    c.setStrokeColor(color)
    c.setLineWidth(width)
    c.line(x1, y1, x2, y2)
    c.setLineWidth(1)


def box(c, x, y, w, h, fill=None):
    if fill:
        c.setFillColor(fill)
        c.roundRect(x, y, w, h, 6, fill=1, stroke=0)
    c.setStrokeColor(BORDER)
    c.roundRect(x, y, w, h, 6, fill=0, stroke=1)


def icon_circle(c, cx, cy, r=3.5, color=BLUE):
    c.setFillColor(color)
    c.circle(cx, cy, r, fill=1, stroke=0)


# ==========================================================
# ASSESSMENT YEAR / FINANCIAL YEAR HELPER
# ==========================================================

def get_assessment_financial_year(invoice_date):
    try:
        year = invoice_date.year
        month = invoice_date.month
    except AttributeError:
        today = date.today()
        year, month = today.year, today.month

    if month >= 4:
        fy_start, fy_end = year, year + 1
    else:
        fy_start, fy_end = year - 1, year

    # Assessment Year = the currently running year (e.g. "2026 - 2027"
    # right now). Financial Year = the preceding year, since that's the
    # income year that's actually being assessed during the current AY
    # (standard convention: AY N covers income earned in FY N-1).
    ay_start, ay_end = fy_start, fy_end
    prev_fy_start, prev_fy_end = fy_start - 1, fy_end - 1

    financial_year = f"{prev_fy_start}-{str(prev_fy_end)[-2:]}"
    assessment_year = f"{ay_start} - {ay_end}"

    return assessment_year, financial_year


# ==========================================================
# NUMBER TO WORDS
# ==========================================================

def number_to_words(amount):
    try:
        amount = int(round(float(amount)))
    except Exception:
        return ""

    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven",
            "Eight", "Nine", "Ten", "Eleven", "Twelve", "Thirteen",
            "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen",
            "Nineteen"]

    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty",
            "Seventy", "Eighty", "Ninety"]

    def convert(num):
        if num < 20:
            return ones[num]
        if num < 100:
            return (tens[num // 10] + " " + ones[num % 10]).strip()
        if num < 1000:
            return (ones[num // 100] + " Hundred " + convert(num % 100)).strip()
        if num < 100000:
            return (convert(num // 1000) + " Thousand " + convert(num % 1000)).strip()
        if num < 10000000:
            return (convert(num // 100000) + " Lakh " + convert(num % 100000)).strip()
        return (convert(num // 10000000) + " Crore " + convert(num % 10000000)).strip()

    if amount == 0:
        return "Rupees Zero Only"

    return convert(amount) + " Rupees Only"


# ==========================================================
# HEADER SECTION  (drawn only on page 1)
# ==========================================================

def draw_header(c, invoice_data, logo_path=None):

    top = PAGE_HEIGHT - 45

    if logo_path and os.path.exists(logo_path):
        try:
            c.drawImage(
                ImageReader(logo_path),
                45, top - 55,
                width=55, height=55,
                preserveAspectRatio=True,
                mask="auto"
            )
        except Exception:
            pass

    company_x = 60

    text(c, company_x, top, invoice_data.get("Company Name", "COMPANY NAME"),
         size=22, bold=True, color=BLUE)

    text(c, company_x, top - 20, safe(invoice_data.get("Profession", "")).upper(),
         size=9, bold=True, color=BLUE)

    line(c, company_x, top - 26, company_x + 170, top - 26, color=BLUE, width=1.2)

    icon_circle(c, company_x + 4, top - 42)
    text(c, company_x + 14, top - 45, invoice_data.get("Company Phone", ""), size=10)

    icon_circle(c, company_x + 4, top - 58)
    text(c, company_x + 14, top - 61, invoice_data.get("Company Email", ""), size=10)

    icon_circle(c, company_x + 4, top - 74)
    text(c, company_x + 14, top - 77, invoice_data.get("Company Address", ""), size=10)

    right_x = 345

    text(c, right_x, top, "INVOICE", size=25, bold=True, color=BLUE)
    line(c, right_x, top - 8, RIGHT_EDGE, top - 8)

    info_y = top - 25

    invoice_details = [
        ("Invoice No.", invoice_data.get("Invoice Number", "-")),
        ("Invoice Date", invoice_data.get("Invoice Date", "-")),
        ("Place of Supply", invoice_data.get("Place of Supply", "-")),
        ("PAN", invoice_data.get("PAN", "-")),
    ]

    for label, value in invoice_details:
        text(c, right_x, info_y, label, size=10, bold=True)
        text(c, right_x + 90, info_y, ":", size=10, bold=True)
        text(c, right_x + 105, info_y, value, size=10)
        info_y -= 20

    line(c, 40, PAGE_HEIGHT - 160, PAGE_WIDTH - 40, PAGE_HEIGHT - 160)


# ==========================================================
# BILL TO SECTION + ASSESSMENT YEAR CARD  (page 1 only)
# Bill To heading is aligned with the top of the Assessment
# Year card, freeing up extra vertical space above the table.
# ==========================================================

def draw_customer_section(c, invoice_data, invoice_date=None):

    card_x = 390
    card_w, card_h = 160, 110
    card_y = PAGE_HEIGHT - 282

    section_y = card_y + card_h  # aligned with the top of the card

    text(c, 55, section_y, "BILL TO", size=14, bold=True, color=BLUE)
    line(c, 55, section_y - 8, 120, section_y - 8)

    start_y = section_y - 32

    customer_fields = [
        ("Name", invoice_data.get("Customer Name", "")),
        ("Address", invoice_data.get("Customer Address", "")),
        ("PAN", invoice_data.get("Customer PAN", "")),
        ("Mobile No.", invoice_data.get("Customer Phone", "")),
        ("Email", invoice_data.get("Customer Email", "")),
    ]

    for label, value in customer_fields:
        text(c, 45, start_y, label, size=10, bold=True, medium=True)
        text(c, 110, start_y, ":", size=10, bold=True)
        text(c, 125, start_y, value, size=10)
        line(c, 125, start_y - 5, 350, start_y - 5)
        start_y -= 26

    # ------------------- ASSESSMENT YEAR CARD -------------------
    assessment_year, financial_year = get_assessment_financial_year(invoice_date)

    box(c, card_x, card_y, card_w, card_h, LIGHT_BLUE)

    text(c, card_x + 18, card_y + 82, "Assessment Year", size=12, bold=True, color=BLUE)
    text(c, card_x + 18, card_y + 48, assessment_year, size=18, bold=True)

    line(c, card_x + 15, card_y + 38, card_x + 145, card_y + 38)

    text(c, card_x + 18, card_y + 18, f"Financial Year {financial_year}", size=9, color=BLUE)

    # Bottom-most point actually used on this page by this section
    # (fields usually run lower than the card).
    return min(start_y + 26 - 15, card_y) - 15


# ==========================================================
# ITEMS TABLE  (paginates automatically; vertical column
# dividers included; description is pixel-wrapped so nothing
# ever spills outside its cell)
# ==========================================================

TABLE_X = MARGIN_X
TABLE_WIDTH = RIGHT_EDGE - MARGIN_X
HEADER_HEIGHT = 32
ROW_HEIGHT = 46
CELL_PAD = 8

# Column widths: #, Description, HSN, Rate, Amount
COL_WIDTHS = [32, 248, 70, 75, 80]
COL_BOUNDS = [TABLE_X]
for w in COL_WIDTHS:
    COL_BOUNDS.append(COL_BOUNDS[-1] + w)
# COL_BOUNDS = [45, 77, 325, 395, 470, 550]

HEADERS = ["#", "Description", "HSN", "Rate", "Amount"]

# ---- Notes / Summary / Payment / Thank-you footer block sizing ----
# (defined here, before the table, so the pagination check below can
# reserve exactly the right amount of space — no more, no less.)
GAP_TABLE_TO_BLOCK = 20   # constant distance: table bottom -> Notes/Summary boxes
NOTES_HEIGHT = 100
TOTAL_HEIGHT = 100
GAP_BOXES_TO_PAYMENT = 12
PAYMENT_HEIGHT = 105
GAP_PAYMENT_TO_ICON = 14
ICON_TO_TEXT_GAP = 12
TEXT_LINE_GAP = 10

# Exact vertical space the footer block needs, end to end: gap + notes/
# summary boxes + gap + payment box + gap + icon + two text lines.
FOOTER_BLOCK_HEIGHT = (
    GAP_TABLE_TO_BLOCK + NOTES_HEIGHT + GAP_BOXES_TO_PAYMENT + PAYMENT_HEIGHT
    + GAP_PAYMENT_TO_ICON + ICON_TO_TEXT_GAP + TEXT_LINE_GAP
)

# Space that must stay free below a row for it to be safely drawn: the
# row's own bottom edge must leave room for the full footer block plus
# a small safety cushion (content in that block is always a fixed
# height — capped line counts — so this margin never varies).
FOOTER_ZONE_HEIGHT = FOOTER_BLOCK_HEIGHT + 15


def _draw_table_header(c, top_y):
    c.setFillColor(BLUE)
    c.roundRect(TABLE_X, top_y, TABLE_WIDTH, HEADER_HEIGHT, 5, fill=1, stroke=0)
    for i, head in enumerate(HEADERS):
        center = (COL_BOUNDS[i] + COL_BOUNDS[i + 1]) / 2
        center_text(c, center, top_y + 11, head, size=9, bold=True, color=WHITE)


def _draw_row_borders(c, y, is_first_col_thick=False):
    """Draws the row rectangle plus internal vertical dividers."""
    c.setStrokeColor(BORDER)
    c.rect(TABLE_X, y, TABLE_WIDTH, ROW_HEIGHT, fill=0, stroke=1)
    for x in COL_BOUNDS[1:-1]:
        c.line(x, y, x, y + ROW_HEIGHT)


def draw_items_table(c, items, start_top):
    """
    Draws the items table starting at `start_top` on the current page.
    Automatically starts a new page (redrawing the table header) if the
    table would otherwise run into the footer zone or off the page.
    Returns (canvas, bottom_y_of_table_on_final_page).
    """

    # `start_top` is the topmost y available (just below the Bill To /
    # Assessment Year block); the header bar's bottom edge sits
    # HEADER_HEIGHT below that.
    table_top = start_top - HEADER_HEIGHT
    _draw_table_header(c, table_top)
    current_y = table_top - ROW_HEIGHT

    for index, item in enumerate(items, start=1):

        # Start a new page if this row would collide with the footer zone
        if current_y < FOOTER_ZONE_HEIGHT:
            c.showPage()
            center_text(c, PAGE_WIDTH / 2, PAGE_HEIGHT - 35,
                        "INVOICE (contd.)", size=12, bold=True, color=BLUE)
            table_top = PAGE_HEIGHT - 60
            _draw_table_header(c, table_top)
            current_y = table_top - ROW_HEIGHT

        _draw_row_borders(c, current_y)

        desc_col_x = COL_BOUNDS[1] + CELL_PAD
        desc_col_width = COL_WIDTHS[1] - 2 * CELL_PAD

        raw_description = safe(item.get("particular", ""))
        description_lines = []
        for paragraph in raw_description.split("\n"):
            description_lines.extend(wrap_text_px(c, paragraph, desc_col_width, size=9))
        description_lines = description_lines[:3]

        desc_y = current_y + ROW_HEIGHT - 16
        for line_index, desc_line in enumerate(description_lines):
            text(
                c, desc_col_x, desc_y, desc_line,
                size=9,
                bold=(line_index == 0),
                color=BLACK if line_index == 0 else GREY
            )
            desc_y -= 12

        mid_y = current_y + ROW_HEIGHT / 2 - 3

        sr_center = (COL_BOUNDS[0] + COL_BOUNDS[1]) / 2
        hsn_center = (COL_BOUNDS[2] + COL_BOUNDS[3]) / 2
        rate_center = (COL_BOUNDS[3] + COL_BOUNDS[4]) / 2
        amount_center = (COL_BOUNDS[4] + COL_BOUNDS[5]) / 2

        rate_str = money(item.get("rate", 0))
        amount_str = money(item.get("amount", 0))

        rate_size = fit_size(c, rate_str, 9, COL_WIDTHS[3] - 2 * CELL_PAD)
        amount_size = fit_size(c, amount_str, 9, COL_WIDTHS[4] - 2 * CELL_PAD, bold=True)

        center_text(c, sr_center, mid_y, str(index), size=9)
        center_text(c, hsn_center, mid_y, item.get("hsn", "-") or "-", size=9)
        center_text(c, rate_center, mid_y, rate_str, size=rate_size)
        center_text(c, amount_center, mid_y, amount_str, size=amount_size, bold=True)

        current_y -= ROW_HEIGHT

    return current_y


# ==========================================================
# NOTES / SUMMARY / PAYMENT / THANK-YOU FOOTER BLOCK
#
# This whole block is positioned relative to wherever the items
# table actually ends (table_bottom_y), with a FIXED, constant gap
# between the table and the block — so on invoices with only one or
# two rows the block sits right under the table, and on invoices
# that (almost) fill the page it sits at the same safe minimum
# distance from the bottom as before. The gap itself never changes.
# ==========================================================

NOTES = [
    "Payment should be completed before due date.",
    "This invoice is generated electronically.",
]

FIXED_UPI_ID = "9767019589@ybl"


def draw_notes_section(c, y):
    x, width, height = MARGIN_X, 240, NOTES_HEIGHT

    box(c, x, y, width, height, LIGHT_GREY)

    text(c, x + 15, y + height - 24, "NOTES", size=12, bold=True, color=BLUE)

    current = y + height - 46
    for note in NOTES:
        wrapped = wrap_text_px(c, "- " + note, width - 30, size=9.5)
        for w_line in wrapped:
            text(c, x + 15, current, w_line, size=9.5)
            current -= 14
        current -= 4


def draw_total_box(c, summary, y):

    x, width, height = 305, RIGHT_EDGE - 305, TOTAL_HEIGHT

    box(c, x, y, width, height, LIGHT_BLUE)

    text(c, x + 15, y + height - 22, "Invoice Summary", size=12, bold=True, color=BLUE)

    grand_total = summary.get("grand_total", 0)

    current = y + height - 44

    text(c, x + 15, current, "Total Amount", size=11, bold=True, color=BLUE)
    right_text(c, x + width - 15, current, money(grand_total), size=13, bold=True, color=BLUE)
    current -= 16

    line(c, x + 10, current, x + width - 10, current)
    current -= 13

    text(c, x + 15, current, "Amount in Words:", size=8, bold=True)
    current -= 11

    words_lines = wrap_text_px(c, number_to_words(grand_total), width - 30, size=8)
    for words_line in words_lines[:2]:
        text(c, x + 15, current, words_line, size=8)
        current -= 10


def draw_payment_section(c, invoice_data, qr_file, grand_total, y):

    x = MARGIN_X
    width, height = TABLE_WIDTH, PAYMENT_HEIGHT

    box(c, x, y, width, height, LIGHT_BLUE)

    mid_x = x + width / 2
    line(c, mid_x, y + 12, mid_x, y + height - 12)

    # ------------------- LEFT: PAYMENT DETAILS -------------------
    text(c, x + 15, y + height - 20, "PAYMENT DETAILS", size=12, bold=True, color=BLUE)

    if qr_file and os.path.exists(qr_file):
        c.drawImage(
            ImageReader(qr_file),
            x + 15, y + 15,
            width=65, height=65
        )

    text(c, x + 95, y + height - 42, "SCAN & PAY", size=10, bold=True, color=BLUE)
    text(c, x + 95, y + height - 55, "Scan the QR code to pay", size=8)
    text(c, x + 95, y + height - 66, "using any UPI app.", size=8)

    text(c, x + 95, y + 26, "UPI ID:", size=9, bold=True)
    text(c, x + 95, y + 14, FIXED_UPI_ID, size=9)

    # ------------------- RIGHT: PAY NOW -------------------
    right_x = mid_x + 15

    text(c, right_x, y + height - 20, "PAY NOW", size=12, bold=True, color=BLUE)
    text(c, right_x, y + height - 36, "Tap/click the button below on a", size=8)
    text(c, right_x, y + height - 46, "phone with a UPI app installed.", size=8)

    button_x = right_x
    button_y = y + 18
    button_w = width / 2 - 30
    button_h = 32

    c.setFillColor(BLUE)
    c.roundRect(button_x, button_y, button_w, button_h, 8, fill=1, stroke=0)

    pay_label = f"PAY {money(grand_total)}"
    pay_size = fit_size(c, pay_label, 11, button_w - 20, bold=True)

    center_text(
        c, button_x + button_w / 2, button_y + button_h / 2 - 4,
        pay_label,
        size=pay_size, bold=True, color=WHITE
    )

    payment_link = invoice_data.get("Payment Link", "")
    if payment_link:
        c.linkURL(
            payment_link,
            (button_x, button_y, button_x + button_w, button_y + button_h),
            relative=0
        )

    hint_text = "Button not opening? Scan the QR instead."
    hint_size = fit_size(c, hint_text, 7, width / 2 - 30, min_size=6)
    text(c, right_x, y + 4, hint_text, size=hint_size, color=GREY)


def draw_thank_you(c, top_y):
    """Draws the closing icon + message, stacked top-to-bottom with
    clear spacing so the icon never overlaps the text."""
    icon_y = top_y
    icon_circle(c, PAGE_WIDTH / 2, icon_y, r=4)

    text1_y = icon_y - ICON_TO_TEXT_GAP
    text2_y = text1_y - TEXT_LINE_GAP

    center_text(c, PAGE_WIDTH / 2, text1_y, "Thank you for choosing", size=8, color=BLACK)
    center_text(c, PAGE_WIDTH / 2, text2_y, "our professional services!", size=8, color=BLACK)


def draw_footer_block(c, invoice_data, summary, qr_file, table_bottom_y):
    """
    Positions Notes / Invoice Summary / Payment / Thank-you as one
    stacked block, starting a constant GAP_TABLE_TO_BLOCK below
    wherever the items table actually ended.
    """

    block_top = table_bottom_y - GAP_TABLE_TO_BLOCK

    notes_total_y = block_top - NOTES_HEIGHT
    draw_notes_section(c, notes_total_y)
    draw_total_box(c, summary, notes_total_y)

    payment_top = notes_total_y - GAP_BOXES_TO_PAYMENT
    payment_y = payment_top - PAYMENT_HEIGHT
    draw_payment_section(c, invoice_data, qr_file, summary.get("grand_total", 0), payment_y)

    icon_top = payment_y - GAP_PAYMENT_TO_ICON
    draw_thank_you(c, icon_top)


# ==========================================================
# FINAL PDF GENERATOR
# ==========================================================

def generate_pdf(invoice_data, summary, qr_file=None, logo_path=None, invoice_date=None):
    """
    Creates a professional invoice PDF (auto-paginates if there are many
    line items). The Notes / Summary / Payment / Thank-you block always
    sits a constant distance below wherever the table ends.

    Parameters:
        invoice_data : dict
        summary      : dict returned by calculate_invoice()
        qr_file      : QR image path (built from the fixed UPI ID)
        logo_path    : Company logo path
        invoice_date : raw date object (used for Assessment Year calc)
    """

    os.makedirs("invoices", exist_ok=True)

    invoice_number = safe(invoice_data.get("Invoice Number", "invoice")) or "invoice"
    # Sanitize so the invoice number can never break the file path
    safe_number = "".join(ch for ch in invoice_number if ch.isalnum() or ch in ("-", "_")) or "invoice"
    pdf_path = os.path.join("invoices", f"{safe_number}.pdf")

    c = canvas.Canvas(pdf_path, pagesize=A4)

    draw_header(c, invoice_data, logo_path)
    table_start_y = draw_customer_section(c, invoice_data, invoice_date)
    table_bottom_y = draw_items_table(c, summary.get("items", []), table_start_y)

    draw_footer_block(c, invoice_data, summary, qr_file, table_bottom_y)

    c.showPage()
    c.save()

    return pdf_path


# ==========================================================
# END OF invoice_pdf.py
# ==========================================================
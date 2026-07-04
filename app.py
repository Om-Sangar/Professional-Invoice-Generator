import re
import os
import streamlit as st
import pandas as pd
from datetime import date

from calculations import calculate_invoice
from invoice_pdf import generate_pdf, FIXED_UPI_ID


# =====================================================
# FIXED / PERMANENT COMPANY DETAILS
# =====================================================

COMPANY_NAME = "Rushikesh Limkar"
COMPANY_PROFESSION = "CHARTERED ACCOUNTANT"

# =====================================================
# VALIDATION HELPERS
# =====================================================

MOBILE_REGEX = re.compile(r"^[6-9]\d{9}$")
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")
PAN_REGEX = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
HSN_REGEX = re.compile(r"^\d{4,8}$")


def normalize_mobile(raw):
    """Strips spaces/dashes and a leading +91 / 91 / 0 so both
    '9876543210' and '+91 98765 43210' end up as the same clean
    10-digit number."""
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return digits


def normalize_email(raw):
    """Emails are case-insensitive by convention — always store/display
    lowercase so 'OM@GMAIL.COM' and 'om@gmail.com' aren't treated as
    visually different values."""
    return (raw or "").strip().lower()


def is_valid_mobile(value):
    return bool(MOBILE_REGEX.match(normalize_mobile(value)))


def is_valid_email(value):
    return bool(EMAIL_REGEX.match(normalize_email(value)))


def is_valid_pan(value):
    return bool(PAN_REGEX.match(value.strip().upper()))


def is_valid_hsn(value):
    return bool(HSN_REGEX.match(value.strip()))


def field_hint(value, is_valid_fn, error_msg, ok_msg="Looks good"):
    """Shows inline pass/fail feedback right under a field, live as
    the person fills the form in — not just after clicking Generate."""
    if value and value.strip():
        if is_valid_fn(value):
            st.caption(f"✅ {ok_msg}")
        else:
            st.caption(f"⚠️ {error_msg}")


def _normalize_phone_on_change(key):
    def _cb():
        st.session_state[key] = normalize_mobile(st.session_state.get(key, ""))
    return _cb


def _normalize_email_on_change(key):
    def _cb():
        st.session_state[key] = normalize_email(st.session_state.get(key, ""))
    return _cb


INVOICE_COUNTER_FILE = "invoice_counter.txt"


def _read_counter():
    try:
        with open(INVOICE_COUNTER_FILE, "r") as f:
            return int((f.read() or "0").strip())
    except (FileNotFoundError, ValueError):
        return 0


def _format_invoice_number(count):
    from datetime import datetime
    stamp = datetime.now().strftime("%Y%m%d")
    return f"INV-{stamp}-{count:03d}"


def peek_invoice_number():
    """Shows what the next invoice number WOULD be, without consuming it."""
    return _format_invoice_number(_read_counter() + 1)


def commit_invoice_number():
    """
    Actually advances the sequential counter (001, 002, 003...) and
    returns the number just consumed. Only called once an invoice is
    successfully generated, so simply reloading the page never skips
    a number. This tiny counter file stores a single integer only —
    no invoice details or customer data are stored anywhere.
    """
    next_count = _read_counter() + 1
    with open(INVOICE_COUNTER_FILE, "w") as f:
        f.write(str(next_count))
    return _format_invoice_number(next_count)


# =====================================================
# PAGE CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="AI Invoice Generator",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded"
)

if "invoice_no_peek" not in st.session_state:
    st.session_state.invoice_no_peek = peek_invoice_number()

# =====================================================
# SIDEBAR
# =====================================================

with st.sidebar:

    st.image(
        "https://img.icons8.com/fluency/96/invoice.png",
        width=80
    )

    st.title("AI Invoice Generator")

    st.markdown("---")

    st.success("✓ Professional PDF")

    st.success("✓ Payment QR")

    st.success("✓ UPI Ready")

    st.markdown("---")

    st.caption("Version 1.1")

# =====================================================
# HEADER
# =====================================================

left, right = st.columns([5, 1])

with left:
    st.title("🧾 AI Invoice Generator")
    st.caption("Generate professional invoices with UPI QR payments.")

with right:
    st.metric("Status", "Ready")

st.divider()

# =====================================================
# COMPANY & CUSTOMER DETAILS
# =====================================================

st.subheader("🏢 Company & Customer Information")

company_col, customer_col = st.columns(2)

# =====================================================
# COMPANY DETAILS (name & profession are fixed)
# =====================================================

with company_col:

    with st.container(border=True):

        st.markdown("## 🏢 Company Details")

        st.text_input("Your Name", value=COMPANY_NAME, disabled=True)
        st.text_input("Profession", value=COMPANY_PROFESSION, disabled=True)

        company_phone = st.text_input(
            "Phone Number",
            placeholder="9876543210",
            key="company_phone",
            on_change=_normalize_phone_on_change("company_phone")
        )
        field_hint(
            company_phone, is_valid_mobile,
            "Enter a valid 10-digit Indian mobile number (starts 6-9). A +91 prefix is fine — it'll be stripped automatically.",
            "Valid mobile number"
        )

        company_email = st.text_input(
            "Email",
            placeholder="contact@company.com",
            key="company_email",
            on_change=_normalize_email_on_change("company_email")
        )
        field_hint(company_email, is_valid_email, "Enter a valid email address, e.g. name@example.com.", "Valid email")

        company_address = st.text_area(
            "Location",
            placeholder="City, State"
        )

        pan_number = st.text_input(
            "Your PAN Number",
            placeholder="ABCDE1234F",
            key="company_pan"
        ).strip().upper()
        field_hint(pan_number, is_valid_pan, "PAN must be in the format ABCDE1234F (5 letters, 4 digits, 1 letter).", "Valid PAN format")

# =====================================================
# CUSTOMER DETAILS
# =====================================================

with customer_col:

    with st.container(border=True):

        st.markdown("## 👤 Customer Details")

        customer_name = st.text_input(
            "Customer Name",
            placeholder="Customer Name",
            key="customer_name"
        )
        if not customer_name.strip():
            st.caption("⚠️ Required.")

        customer_phone = st.text_input(
            "Phone Number",
            placeholder="9876543210 (10 digits)",
            key="customer_phone",
            on_change=_normalize_phone_on_change("customer_phone")
        )
        field_hint(
            customer_phone, is_valid_mobile,
            "Enter a valid 10-digit Indian mobile number (starts 6-9). A +91 prefix is fine — it'll be stripped automatically.",
            "Valid mobile number"
        )

        customer_email = st.text_input(
            "Email",
            placeholder="customer@email.com",
            key="customer_email",
            on_change=_normalize_email_on_change("customer_email")
        )
        field_hint(customer_email, is_valid_email, "Enter a valid email address, e.g. name@example.com.", "Valid email")

        customer_address = st.text_area(
            "Customer Address",
            placeholder="Enter customer address...",
            key="customer_address"
        )

        customer_pan = st.text_input(
            "Customer PAN",
            placeholder="ABCDE1234F",
            key="customer_pan"
        ).strip().upper()
        field_hint(customer_pan, is_valid_pan, "PAN must be in the format ABCDE1234F (5 letters, 4 digits, 1 letter).", "Valid PAN format")

st.divider()

# ============================
# Invoice Details
# ============================

st.header("📄 Invoice Details")

col1, col2, col3 = st.columns(3)

with col1:
    invoice_no = st.text_input(
        "Invoice Number",
        value=st.session_state.invoice_no_peek,
        help="Auto-suggested as the next sequential number. Edit only if you need a custom number."
    )
    if invoice_no.strip() and not re.match(r"^[A-Za-z0-9\-_]+$", invoice_no.strip()):
        st.caption("⚠️ Use only letters, numbers, hyphens, and underscores (this becomes the PDF's file name).")

with col2:
    invoice_date = st.date_input("Invoice Date", value=date.today())

with col3:
    place_supply = st.text_input("Place of Supply")

payment_terms = st.selectbox(
    "Payment Terms",
    ["Immediate", "7 Days", "15 Days", "30 Days"]
)

st.markdown("---")

# ============================
# Invoice Items (no quantity, no GST — user enters the final
# amount for each line item directly)
# ============================

st.header("🛒 Invoice Items")
st.caption("Enter the final amount for each item — no GST is added.")

items = []

for i in range(3):

    st.subheader(f"Item {i+1}")

    c1, c2, c3 = st.columns([4, 2, 2])

    with c1:
        particular = st.text_input("Particular", key=f"particular_{i}")

    with c2:
        hsn = st.text_input("HSN/SAC", key=f"hsn_{i}")
        if hsn.strip() and not is_valid_hsn(hsn):
            st.caption("⚠️ HSN/SAC is usually a 4–8 digit number.")

    with c3:
        rate = st.number_input(
            "Amount (₹)",
            min_value=0.0,
            value=0.0,
            step=100.0,
            key=f"rate_{i}"
        )
        if particular.strip() and rate <= 0:
            st.caption("⚠️ Amount must be greater than 0.")

    if particular.strip() != "":
        items.append({
            "particular": particular,
            "hsn": hsn,
            "rate": rate,
        })

st.markdown("---")

# ============================
# Payment Details
# ============================

st.header("💳 Payment Details")

st.info(f"All payments are collected via the fixed UPI ID: **{FIXED_UPI_ID}**")

st.markdown("---")

# ============================
# Company Logo Upload
# ============================

logo = st.file_uploader(
    "Upload Company Logo",
    type=["png", "jpg", "jpeg"]
)

st.markdown("---")

# ============================
# Generate Button
# ============================

generate = st.button("Generate Invoice", use_container_width=True)

# =====================================================
# Validation + Calculations + Invoice Generation
# =====================================================

if generate:

    # Defensive re-normalization in case a field's on_change callback
    # hasn't fired yet (e.g. typed then immediately clicked Generate).
    company_phone = normalize_mobile(company_phone)
    customer_phone = normalize_mobile(customer_phone)
    company_email = normalize_email(company_email)
    customer_email = normalize_email(customer_email)

    errors = []

    if len(items) == 0:
        errors.append("Please add at least one invoice item with a particular and amount.")

    for idx, item in enumerate(items, start=1):
        if item["rate"] <= 0:
            errors.append(f"Item {idx}: amount must be greater than 0.")
        if item["hsn"].strip() and not is_valid_hsn(item["hsn"]):
            errors.append(f"Item {idx}: HSN/SAC should be a 4–8 digit number.")

    if not customer_name.strip():
        errors.append("Customer Name is required.")

    if not customer_phone:
        errors.append("Customer phone number is required.")
    elif not is_valid_mobile(customer_phone):
        errors.append("Customer phone number must be a valid 10-digit Indian mobile number (starts 6-9).")

    if company_phone and not is_valid_mobile(company_phone):
        errors.append("Your phone number must be a valid 10-digit Indian mobile number (starts 6-9).")

    if customer_email and not is_valid_email(customer_email):
        errors.append("Customer email address is not valid.")

    if company_email and not is_valid_email(company_email):
        errors.append("Your email address is not valid.")

    if customer_pan.strip() and not is_valid_pan(customer_pan):
        errors.append("Customer PAN must be in the format ABCDE1234F.")

    if pan_number.strip() and not is_valid_pan(pan_number):
        errors.append("Your PAN must be in the format ABCDE1234F.")

    if not invoice_no.strip():
        errors.append("Invoice Number cannot be empty.")
    elif not re.match(r"^[A-Za-z0-9\-_]+$", invoice_no.strip()):
        errors.append("Invoice Number can only contain letters, numbers, hyphens, and underscores.")

    if errors:
        for err in errors:
            st.error(err)
        st.stop()

    # Sequential numbering: only advance the counter if the user kept
    # the auto-suggested number. If they typed a custom number, leave
    # the counter untouched (their custom number is used as-is).
    if invoice_no.strip() == st.session_state.invoice_no_peek:
        invoice_no = commit_invoice_number()
        st.session_state.invoice_no_peek = peek_invoice_number()

    # Perform calculations (no GST)
    result = calculate_invoice(items)
    grand_total = result["grand_total"]

    st.success("Invoice Calculated Successfully!")

    # =====================================================
    # Invoice Summary
    # =====================================================

    st.markdown("## 📋 Invoice Summary")

    summary = []
    for item in result["items"]:
        summary.append({
            "Particular": item["particular"],
            "HSN/SAC": item["hsn"],
            "Amount (₹)": item["amount"]
        })

    summary_df = pd.DataFrame(summary)
    st.dataframe(summary_df, use_container_width=True, hide_index=True)

    st.markdown("### 💰 Total")
    st.metric("Grand Total", f"₹ {grand_total:,.2f}")

    # =====================================================
    # Build invoice_data (nothing is written to disk / CSV)
    # =====================================================

    invoice_data = {
        "Invoice Number": invoice_no,
        "Invoice Date": invoice_date.strftime("%d %b %Y"),
        "Place of Supply": place_supply,
        "PAN": pan_number,

        "Company Name": COMPANY_NAME,
        "Company Phone": company_phone,
        "Company Email": company_email,
        "Profession": COMPANY_PROFESSION,
        "Company Address": company_address,

        "Customer Name": customer_name,
        "Customer Phone": customer_phone,
        "Customer Email": customer_email,
        "Customer Address": customer_address,
        "Customer PAN": customer_pan,

        "Grand Total": grand_total,

        "Payment Terms": payment_terms,
        "UPI ID": FIXED_UPI_ID,
        "Payment Link": "",
    }

    # =====================================================
    # Generate UPI Payment Link (fixed UPI ID only)
    # =====================================================

    from urllib.parse import quote

    payment_note = f"Invoice No. {invoice_no}"

    payment_link = (
        f"upi://pay?"
        f"pa={FIXED_UPI_ID}"
        f"&pn={quote(COMPANY_NAME)}"
        f"&am={grand_total:.2f}"
        f"&cu=INR"
        f"&tn={quote(payment_note)}"
    )
    invoice_data["Payment Link"] = payment_link

    # =====================================================
    # Generate Payment QR Code
    # =====================================================

    import qrcode

    os.makedirs("generated_qr", exist_ok=True)

    qr = qrcode.make(payment_link)
    qr_file = os.path.join("generated_qr", f"{invoice_no}.png")
    qr.save(qr_file)

    st.image(qr_file, width=220, caption="Payment QR Code (scan with any UPI app)")

    # =====================================================
    # Generate Professional PDF
    # =====================================================

    logo_path = None
    if logo is not None:
        os.makedirs("assets", exist_ok=True)
        logo_path = os.path.join("assets", logo.name)
        with open(logo_path, "wb") as file:
            file.write(logo.getbuffer())

    pdf_path = generate_pdf(
        invoice_data=invoice_data,
        summary=result,
        qr_file=qr_file,
        logo_path=logo_path,
        invoice_date=invoice_date
    )

    st.success("Professional PDF Generated Successfully!")

    with open(pdf_path, "rb") as pdf:
        st.download_button(
            label="📥 Download Invoice PDF",
            data=pdf,
            file_name=f"{invoice_no}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
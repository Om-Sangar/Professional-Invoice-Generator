
# 🧾 Professional Invoice Generator

A Python-based invoice generation application built with Streamlit. It helps users create professional PDF invoices with customer details, invoice information, automatic calculations, and UPI payment QR codes.

## ✨ Features

- Generate professional PDF invoices.
- Enter company and customer information.
- Add invoice details and item descriptions.
- Automatically calculate invoice totals.
- Generate sequential invoice numbers.
- Generate UPI payment links.
- Create QR codes for easy payments.
- Upload a company logo.
- Download invoices as PDF files.
- Validate customer and company information.

## 🛠️ Technologies Used

- Python
- Streamlit
- Pandas
- ReportLab
- QR Code

## 📁 Project Structure

```text
Professional-Invoice-Generator/
│
├── app.py                 # Main Streamlit application
├── calculations.py        # Invoice calculation logic
├── invoice_pdf.py         # PDF invoice generation
├── invoice_counter.txt    # Sequential invoice counter
├── requirements.txt       # Project dependencies
├── README.md              # Project documentation
│
├── assets/                # Uploaded company logos
└── generated_qr/          # Generated payment QR codes
```

## 🚀 Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/Om-Sangar/Professional-Invoice-Generator.git
```

### 2. Navigate to the project directory

```bash
cd Professional-Invoice-Generator
```

### 3. Create a virtual environment (recommended)

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the application

```bash
streamlit run app.py
```

The application will open in your browser.

## 💡 How to Use

1. Run the application.
2. Enter company information.
3. Enter customer details.
4. Fill in invoice information.
5. Add the invoice items and amounts.
6. Review the calculated invoice total.
7. Generate the payment QR code.
8. Generate and download the professional PDF invoice.

## 🔮 Future Improvements

- Invoice history and management.
- Edit previously generated invoices.
- Customer database management.
- Revenue analytics dashboard.
- Export invoice records to Excel.
- Email invoices directly to customers.

## 🤝 Contributing

Contributions are welcome!

1. Fork the repository.
2. Create a new branch.
3. Make your changes.
4. Test your changes.
5. Submit a Pull Request.

## 👨‍💻 Project Contributors

- Om Sangar - Original Project Creator
- Prathamesh Mankar - Original Project Creator .

## 📄 License

No license has been specified yet. Please contact the repository owner regarding usage and distribution permissions.

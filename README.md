# AI-Integrated CV Management Software

An automated resume processing system that receives resumes via WhatsApp, extracts structured data using AI, and stores it in Google Sheets.

---

## Overview

This system automates the entire CV intake and processing workflow:

1. **Receive**: Candidates send resumes via WhatsApp
2. **Extract**: AI extracts structured data (name, email, skills, experience, etc.)
3. **Store**: Data is automatically saved to Google Sheets
4. **Confirm**: Candidates receive instant confirmation with extracted details



**Workflow:**
1. User sends resume (PDF/DOCX) via WhatsApp
2. Twilio forwards message to Flask webhook
3. System downloads the file
4. Text is extracted from PDF/DOCX
5. OpenAI GPT-4 extracts structured data
6. Data is appended to Google Sheets
7. Confirmation message sent back to user

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend Framework** | Flask 3.0 |
| **WhatsApp API** | Twilio API |
| **AI/NLP** | OpenAI GPT-4o-mini |
| **PDF Processing** | pdfplumber, PyPDF2 |
| **DOCX Processing** | python-docx |
| **Spreadsheet Storage** | Google Sheets API |
| **Environment Management** | python-dotenv |
| **Authentication** | Google OAuth2 |

---

## Installation

### 1. Clone or Create Project Directory

```bash
mkdir cv-management-system
cd cv-management-system
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Create Project Structure

```bash
mkdir -p downloads logs credentials
```

---

## Project Structure

```
cv-management-system/
│
├── main.py                          # Flask application entry point
├── whatsapp_handler.py              # Twilio WhatsApp integration
├── extract.py                       # CV text extraction & AI parsing
├── google_sheets.py                 # Google Sheets operations
├── utils.py                         # Utility functions
│
├── requirements.txt                 # Python dependencies
├── .env                            # Environment variables (DO NOT COMMIT)
├── .env.template                   # Template for .env
├── README.md                       # This file
│
├── credentials/                    # API credentials
│   └── google-service-account.json # Google service account key
│
├── downloads/                      # Temporary file storage
├── logs/                          # Application logs
│   └── cv_management.log
│
└── .gitignore                     # Git ignore rules
```
---

## License

This project is for demonstration and portfolio purposes.

---

## License

This project is for demonstration and portfolio purposes.

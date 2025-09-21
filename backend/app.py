import os
from datetime import datetime
from typing import IO

import google.generativeai as genai
import PyPDF2
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

# --- CONFIGURATION & INITIALIZATION ---
load_dotenv()
app = Flask(__name__)

# --- DATABASE CONFIGURATION FOR RENDER (PostgreSQL) ---
# This block correctly reads the DATABASE_URL environment variable from Render.
db_url = os.getenv("DATABASE_URL")
if not db_url:
    # This error will show in your Render logs if the DATABASE_URL is not set.
    raise RuntimeError("FATAL: DATABASE_URL environment variable is not set.")

# SQLAlchemy requires the scheme to be 'postgresql://'
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config.from_mapping(
    SQLALCHEMY_DATABASE_URI=db_url,
    SQLALCHEMY_TRACK_MODIFICATIONS=False
)
# --- END DATABASE CONFIGURATION ---

CORS(app, origins=["https://legalmind-ai-86ev.onrender.com", "http://localhost:8000", "http://127.0.0.1:5500"])
db = SQLAlchemy(app)


# --- DATABASE MODELS ---

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(300), nullable=False)
    upload_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(50), nullable=False, default='Pending')
    summary = db.Column(db.Text, nullable=True)
    full_text = db.Column(db.Text, nullable=True)
    model_used = db.Column(db.String(100), nullable=True)

    def to_dict(self):
        return {
            "id": self.id, "filename": self.filename,
            "upload_date": self.upload_date.strftime('%b %d, %Y'),
            "status": self.status, "summary": self.summary,
            "full_text": self.full_text, "model_used": self.model_used
        }

class HistoryEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(100), nullable=False)
    document_name = db.Column(db.String(300), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return { "id": self.id, "event_type": self.event_type, "document_name": self.document_name, "timestamp": self.timestamp.strftime('%b %d, %Y, %I:%M %p') }

# --- DATABASE SETUP COMMAND ---
@app.cli.command("init-db")
def init_db_command():
    """Creates the database tables."""
    db.create_all()
    print("Database tables initialized successfully.")

# --- GEMINI API SETUP ---
try:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in .env file or environment.")
    genai.configure(api_key=api_key)
except Exception as e:
    print(f"FATAL: Error configuring Gemini API - {e}")
    raise

# --- HELPER FUNCTIONS ---
def get_gemini_model(model_name: str):
    try:
        allowed_models = ['gemini-1.5-pro', 'gemini-1.5-flash']
        if model_name not in allowed_models:
            model_name = 'gemini-1.5-flash'
        return genai.GenerativeModel(model_name)
    except Exception as e:
        raise ValueError(f"Failed to initialize Gemini model '{model_name}': {e}")

def extract_text_from_pdf(file_stream: IO):
    try:
        reader = PyPDF2.PdfReader(file_stream)
        text = "".join(page.extract_text() for page in reader.pages if page.extract_text())
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return None

def log_event(event_type: str, document_name: str):
    event = HistoryEvent(event_type=event_type, document_name=document_name)
    db.session.add(event)
    db.session.commit()

def _build_analysis_prompt(document_text: str, user_prompt: str):
    return f"""
**Role:** You are an expert legal analyst AI specializing in **Indian Law**.
**Task:** Analyze the provided legal document from the perspective of **Indian law**.
---
**User's Specific Request:** "{user_prompt}"
---
**Document Text:**
{document_text}
---
**Your Structured Analysis (Indian Legal Context):**
### **1.Summary**
* **Potential Risks:** *(Identify clauses on payment, penalties, indemnification)*
* **General Advice:** *(e.g., "Consult a lawyer practicing in India.")*
### **2. Key Details at a Glance**
| Detail | Information Found (with Clause Reference) |
| :--- | :--- |
| **Governing Law** | *(e.g., Laws of India, Jurisdiction in Delhi (Clause 15.1))* |
| **Contract Term** | *(e.g., 24 months from effective date (Section 3))* |
| **Payment Amount**| *(e.g., ₹50,000 INR per month (Annexure A))* |
| **Notice Period** | *(e.g., 60 days for termination (Clause 12.2))* |
### **3. Key Parties & Their Roles**
* **Party A:** *(Identify party and role.)*
* **Party B:** *(Identify party and role.)*
### **4. Key Clauses & Their Implications (under Indian Law)**
* **[Clause Name]:** *(Explain the meaning and impact. Cite the source.)*
### **5. Potential Risks & Red Flags 🚩 (Indian Context)**
* **Financial Risk:** *(Identify clauses on payment, penalties. Cite the source.)*
* **Legal/Liability Risk:** *(Identify clauses on indemnification, liability. Cite the source.)*
### **6. Dispute Resolution (Arbitration / Court Jurisdiction)**
* *(Explain how disputes are resolved. Cite Indian law.)*
### **7. Confidentiality & Intellectual Property**
* *(Highlight clauses on confidentiality and IP ownership.)*
### **8. Compliance & Regulatory Requirements (Indian Laws)**
* *(Note compliance obligations with Indian laws.)*
### **9. Actionable Next Steps (Prioritized)**
1.  **Immediate Action:** *(Suggest the most critical next step.)*
2.  **Recommendation:** *(Suggest an important action.)*
3.  **General Advice:** *(e.g., "Consult a lawyer practicing in India.")*
"""

def _build_qa_prompt(document_text: str, question: str):
    return f"""
**Context:** You are an AI assistant answering questions about the following legal document.
**Document Text:**
---
{document_text}
---
**User's Question:** "{question}"
**Your Answer:**
"""

# --- API ROUTES ---
@app.route('/simplify', methods=['POST'])
def simplify_document():
    # ... [function is unchanged]
@app.route('/ask', methods=['POST'])
def ask_question():
    # ... [function is unchanged]
@app.route('/documents', methods=['GET'])
def get_documents():
    # ... [function is unchanged]
@app.route('/history', methods=['GET'])
def get_history():
    # ... [function is unchanged]
@app.route('/document/<int:doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    # ... [function is unchanged]

# This is a root route to confirm the server is running.
@app.route('/')
def index():
    return jsonify({"status": "ok", "message": "LegalMind AI Backend is running."})

# --- APPLICATION RUNNER ---
# This part is for local development only and will not be used by Render's Gunicorn.
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000, threaded=False)

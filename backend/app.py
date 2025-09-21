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
db_url = os.getenv("DATABASE_URL")
if not db_url:
    raise RuntimeError("FATAL: DATABASE_URL environment variable is not set.")
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
    with app.app_context(): # Ensure app context for CLI command
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
    with app.app_context(): # Ensure app context for db operations outside request context
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
    if 'pdfFile' not in request.files:
        return jsonify({"error": "No PDF file provided."}), 400
    pdf_file = request.files['pdfFile']
    if not pdf_file.filename:
        return jsonify({"error": "No selected file."}), 400

    selected_model_name = request.form.get('model', 'gemini-1.5-flash')
    
    with app.app_context():
        log_event("UPLOAD_SUCCESS", pdf_file.filename)
    
    document_text = extract_text_from_pdf(pdf_file.stream)
    
    if not document_text or not document_text.strip():
        with app.app_context():
            failed_doc = Document(filename=pdf_file.filename, status='Analysis Failed', summary='Could not extract text from PDF.', model_used=selected_model_name)
            db.session.add(failed_doc)
            db.session.commit()
            log_event("TEXT_EXTRACT_FAIL", pdf_file.filename)
        return jsonify({"error": "Could not extract text from the PDF."}), 400
        
    with app.app_context():
        new_doc = Document(filename=pdf_file.filename, status='In Progress', full_text=document_text, model_used=selected_model_name)
        db.session.add(new_doc)
        db.session.commit()
    
    prompt_from_user = request.form.get('prompt', "Provide a comprehensive analysis.")
    full_prompt = _build_analysis_prompt(document_text, prompt_from_user)
    
    try:
        model_instance = get_gemini_model(selected_model_name)
        response = model_instance.generate_content(full_prompt)
        with app.app_context():
            # Re-fetch the document within this new context to ensure it's session-bound
            doc_to_update = db.session.get(Document, new_doc.id)
            if doc_to_update:
                doc_to_update.summary = response.text
                doc_to_update.status = 'Analyzed'
                db.session.commit()
                log_event("ANALYSIS_SUCCESS", doc_to_update.filename)
        return jsonify({"summary": response.text, "document_text": document_text})
    except Exception as e:
        print(f"An error occurred during Gemini API call: {e}")
        with app.app_context():
            # Re-fetch the document to update its status
            doc_to_fail = db.session.get(Document, new_doc.id)
            if doc_to_fail:
                doc_to_fail.status = 'Analysis Failed'
                doc_to_fail.summary = f"Analysis failed: {e}"
                db.session.commit()
                # Use the filename from the request, not the detached object
                log_event("ANALYSIS_FAIL", pdf_file.filename)
        return jsonify({"error": "Failed to get a response from the AI model."}), 500

@app.route('/ask', methods=['POST'])
def ask_question():
    data = request.get_json()
    if not data or 'document_text' not in data or 'question' not in data:
        return jsonify({"error": "Missing document_text or question in request."}), 400

    selected_model_name = data.get('model', 'gemini-1.5-flash')
    qa_prompt = _build_qa_prompt(data['document_text'], data['question'])
    
    try:
        model_instance = get_gemini_model(selected_model_name)
        response = model_instance.generate_content(qa_prompt)
        return jsonify({"answer": response.text})
    except ValueError as e:
        print(f"Gemini API initialization error for /ask: {e}")
        return jsonify({"error": f"AI model configuration error for chat: {e}"}), 500
    except Exception as e:
        print(f"An error occurred during /ask API call: {e}")
        return jsonify({"error": "Failed to get a response for your question. Check server logs for details."}), 500

@app.route('/documents', methods=['GET'])
def get_documents():
    with app.app_context(): # Ensure app context for db query
        documents = Document.query.order_by(Document.upload_date.desc()).all()
    return jsonify([doc.to_dict() for doc in documents])

@app.route('/history', methods=['GET'])
def get_history():
    with app.app_context(): # Ensure app context for db query
        events = HistoryEvent.query.order_by(HistoryEvent.timestamp.desc()).all()
    return jsonify([event.to_dict() for event in events])

@app.route('/document/<int:doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    with app.app_context(): # Ensure app context for db operations
        doc = Document.query.get_or_404(doc_id)
        db.session.delete(doc)
        db.session.commit()
        log_event("DELETE_DOCUMENT", doc.filename)
    return jsonify({"message": "Document deleted successfully."})

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

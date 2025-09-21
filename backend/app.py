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
    with app.app_context():
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
    # ... [Function is unchanged]
def extract_text_from_pdf(file_stream: IO):
    # ... [Function is unchanged]
def log_event(event_type: str, document_name: str):
    # ... [Function is unchanged]
def _build_analysis_prompt(document_text: str, user_prompt: str):
    # ... [Your detailed prompt is unchanged]
def _build_qa_prompt(document_text: str, question: str):
    # ... [Function is unchanged]

# --- API ROUTES ---
@app.route('/simplify', methods=['POST'])
def simplify_document():
    if 'pdfFile' not in request.files: return jsonify({"error": "No PDF file provided."}), 400
    pdf_file = request.files['pdfFile']
    if not pdf_file.filename: return jsonify({"error": "No selected file."}), 400

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

# [All other routes: /ask, /documents, etc., are unchanged]

# --- APPLICATION RUNNER ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000, threaded=False)

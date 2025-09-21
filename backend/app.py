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
    # ... (model is unchanged)
class HistoryEvent(db.Model):
    # ... (model is unchanged)

# --- DATABASE SETUP COMMAND ---
@app.cli.command("init-db")
def init_db_command():
    # ... (command is unchanged)

# --- GEMINI API SETUP ---
# ... (setup is unchanged)

# --- HELPER FUNCTIONS ---
def get_gemini_model(model_name: str):
    # ... (function is unchanged)
def extract_text_from_pdf(file_stream: IO):
    # ... (function is unchanged)
def log_event(event_type: str, document_name: str):
    # ... (function is unchanged)
def _build_analysis_prompt(document_text: str, user_prompt: str):
    # ... (prompt is unchanged)
def _build_qa_prompt(document_text: str, question: str):
    # ... (prompt is unchanged)

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
            # ... (text extraction failure logic is unchanged)

    # --- SIMPLIFIED DATABASE AND API CALL LOGIC ---
    new_doc_id = None
    try:
        with app.app_context():
            new_doc = Document(filename=pdf_file.filename, status='In Progress', full_text=document_text, model_used=selected_model_name)
            db.session.add(new_doc)
            db.session.commit()
            new_doc_id = new_doc.id # Save the ID for potential error handling

        prompt_from_user = request.form.get('prompt', "Provide a comprehensive analysis.")
        full_prompt = _build_analysis_prompt(document_text, prompt_from_user)
        
        model_instance = get_gemini_model(selected_model_name)
        response = model_instance.generate_content(full_prompt)
        
        with app.app_context():
            doc_to_update = db.session.get(Document, new_doc_id)
            if doc_to_update:
                doc_to_update.summary = response.text
                doc_to_update.status = 'Analyzed'
                db.session.commit()
                log_event("ANALYSIS_SUCCESS", doc_to_update.filename)
        return jsonify({"summary": response.text, "document_text": document_text})

    except Exception as e:
        print(f"An error occurred during API call or processing: {e}")
        if new_doc_id:
            with app.app_context():
                doc_to_fail = db.session.get(Document, new_doc_id)
                if doc_to_fail:
                    doc_to_fail.status = 'Analysis Failed'
                    doc_to_fail.summary = f"Analysis failed: {e}"
                    db.session.commit()
                    log_event("ANALYSIS_FAIL", pdf_file.filename)
        return jsonify({"error": "Failed to get a response from the AI model."}), 500
    # --- END OF SIMPLIFIED LOGIC ---

# [All other routes: /ask, /documents, etc., are unchanged]

# --- APPLICATION RUNNER ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000, threaded=False)

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
app.config.from_mapping(
    SQLALCHEMY_DATABASE_URI='sqlite:///documents.db',
    SQLALCHEMY_TRACK_MODIFICATIONS=False
)

CORS(app)
db = SQLAlchemy(app)


# --- DATABASE MODELS ---

class Document(db.Model):
    """Represents an analyzed document in the database."""
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(300), nullable=False)
    upload_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(50), nullable=False, default='Pending')
    summary = db.Column(db.Text, nullable=True)
    full_text = db.Column(db.Text, nullable=True)
    model_used = db.Column(db.String(100), nullable=True) # New column to store which model was used

    def to_dict(self):
        """Serializes the Document object to a dictionary."""
        return {
            "id": self.id,
            "filename": self.filename,
            "upload_date": self.upload_date.strftime('%b %d, %Y'),
            "status": self.status,
            "summary": self.summary,
            "full_text": self.full_text,
            "model_used": self.model_used # Include in dictionary
        }

class HistoryEvent(db.Model):
    """Represents a logged event in the application history."""
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(100), nullable=False)
    document_name = db.Column(db.String(300), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        """Serializes the HistoryEvent object to a dictionary."""
        return { "id": self.id, "event_type": self.event_type, "document_name": self.document_name, "timestamp": self.timestamp.strftime('%b %d, %Y, %I:%M %p') }


# --- GEMINI API SETUP ---

# Configure Google Generative AI once at app startup
try:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Warning: GOOGLE_API_KEY not found in .env file. AI features may fail.")
    else:
        genai.configure(api_key=api_key)
except Exception as e:
    print(f"FATAL: Error configuring Gemini API during startup - {e}")
    # In a production app, you might want to log this and raise a critical error
    # but for development, we'll let individual API calls handle it.


# --- HELPER FUNCTIONS ---

def get_gemini_model(model_name: str):
    """Dynamically gets a GenerativeModel instance based on the provided name."""
    # Ensure API key is present before attempting to get a model
    # The genai.configure() call handles setting the default API key.
    # If it failed or was skipped, subsequent model creations will raise errors.
    # We can rely on that or explicitly check os.getenv("GOOGLE_API_KEY")
    if not os.getenv("GOOGLE_API_KEY"):
        raise ValueError("GOOGLE_API_KEY is not set. Cannot initialize Gemini model.")

    try:
        # Validate model name against allowed ones or fall back to a default
        allowed_models = ['gemini-1.5-pro', 'gemini-1.5-flash']
        if model_name not in allowed_models:
            print(f"Warning: Invalid model '{model_name}' requested. Defaulting to 'gemini-1.5-flash'.")
            model_name = 'gemini-1.5-flash'
        return genai.GenerativeModel(model_name)
    except Exception as e:
        print(f"Error initializing Gemini model '{model_name}': {e}")
        # Re-raise to be caught by route handlers with more specific messages
        raise ValueError(f"Failed to initialize Gemini model '{model_name}'. Ensure API key is valid and model exists: {e}")

def extract_text_from_pdf(file_stream: IO) -> str | None:
    """Extracts text content from a PDF file stream."""
    try:
        reader = PyPDF2.PdfReader(file_stream)
        text = "".join(page.extract_text() for page in reader.pages if page.extract_text())
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return None

def log_event(event_type: str, document_name: str):
    """Creates and saves a new history event to the database."""
    event = HistoryEvent(event_type=event_type, document_name=document_name)
    db.session.add(event)
    db.session.commit()

def _build_analysis_prompt(document_text: str, user_prompt: str) -> str:
    """Builds the detailed analysis prompt for the Gemini API."""
    return f"""
**Role:** You are an expert legal analyst AI specializing in **Indian Law**.
**Task:** Analyze the provided legal document from the perspective of **Indian law**. Your analysis must be clear, structured, and reference specific clauses. Cite relevant Indian statutes where applicable.

---
**User's Specific Request:** "{user_prompt}"
---
**Document Text:**
{document_text}
---
**Your Structured Analysis (Indian Legal Context):**

### **1.Summary**
*(1.Provide a 1-4 sentence overview of the document's core purpose with key details and risks,
* **Potential Risks: In1-3 sentence** *(Identify clauses on payment, penalties, Identify clauses on indemnification)*
* **General Advice:** *(e.g., "Consult a lawyer practicing in India.")*

### **2. Key Details at a Glance**
| Detail | Information Found (with Clause Reference) |
| :--- | :--- |
| **Governing Law** | *(e.g., Laws of India, Jurisdiction in Delhi (Clause 15.1))* |
| **Contract Term** | *(e.g., 24 months from effective date (Section 3))* |
| **Payment Amount**| *(e.g., ₹50,000 INR per month (Annexure A))* |
| **Notice Period** | *(e.g., 60 days for termination (Clause 12.2))* |

### **3. Key Parties & Their Roles**
* **Party A:** *(Identify the party and their role.)*
* **Party B:** *(Identify the other party and their role.)*

### **4. Key Clauses & Their Implications (under Indian Law)**
* **[Clause Name]:** *(Explain the meaning and impact of a major clause. Cite the source.)*

### **5. Potential Risks & Red Flags 🚩 (Indian Context)**
* **Financial Risk:** *(Identify clauses on payment, penalties. Cite the source.)*
* **Legal/Liability Risk:** *(Identify clauses on indemnification, liability. Cite the source.)*

### **6. Dispute Resolution (Arbitration / Court Jurisdiction)**
* *(Explain how disputes are resolved. Cite Indian law, e.g., Arbitration & Conciliation Act, 1996.)*

### **7. Confidentiality & Intellectual Property**
* *(Highlight clauses on confidentiality and IP ownership. Note who owns the IP.)*

### **8. Compliance & Regulatory Requirements (Indian Laws)**
* *(Note compliance obligations with Indian laws like the Companies Act, 2013; Labour Laws; or the DPDP Act, 2023, if applicable.)*

### **9. Actionable Next Steps (Prioritized)**
1.  **Immediate Action:** *(Suggest the most critical next step.)*
2.  **Recommendation:** *(Suggest an important action.)*
3.  **General Advice:** *(e.g., "Consult a lawyer practicing in India.")*
"""

def _build_qa_prompt(document_text: str, question: str) -> str:
    """Builds the prompt for the follow-up Q&A feature."""
    return f"""
**Context:** You are an AI assistant answering questions about the following legal document. Your answers must be based *only* on the information contained within this document. If the answer is not in the document, say so.
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
    """Analyzes a document, saves it with its full text, and logs events."""
    # The get_gemini_model will handle checks for API key availability.
    
    if 'pdfFile' not in request.files: return jsonify({"error": "No PDF file provided."}), 400
    
    pdf_file = request.files['pdfFile']
    if not pdf_file.filename: return jsonify({"error": "No selected file."}), 400

    # Get selected model from the request, default to 'gemini-1.5-flash' if not provided
    selected_model_name = request.form.get('model', 'gemini-1.5-flash')
    
    log_event("UPLOAD_SUCCESS", pdf_file.filename)
    
    document_text = extract_text_from_pdf(pdf_file.stream)
    
    if not document_text or not document_text.strip():
        failed_doc = Document(filename=pdf_file.filename, status='Analysis Failed', summary='Could not extract text from PDF.', model_used=selected_model_name)
        db.session.add(failed_doc)
        db.session.commit()
        log_event("TEXT_EXTRACT_FAIL", pdf_file.filename)
        return jsonify({"error": "Could not extract text from the PDF."}), 400
        
    new_doc = Document(filename=pdf_file.filename, status='In Progress', full_text=document_text, model_used=selected_model_name)
    db.session.add(new_doc)
    db.session.commit()
    
    prompt_from_user = request.form.get('prompt', "Provide a comprehensive analysis.")
    full_prompt = _build_analysis_prompt(document_text, prompt_from_user)
    
    try:
        # Get the dynamically selected model
        model_instance = get_gemini_model(selected_model_name)
        response = model_instance.generate_content(full_prompt)
        new_doc.summary = response.text
        new_doc.status = 'Analyzed'
        log_event("ANALYSIS_SUCCESS", new_doc.filename)
        db.session.commit()
        return jsonify({"summary": new_doc.summary, "document_text": document_text})
    except ValueError as e: # Catch ValueError specifically for API key/model issues from get_gemini_model
        print(f"Gemini API initialization error: {e}")
        new_doc.status = 'Analysis Failed'
        new_doc.summary = f"API Error: {e}"
        log_event("ANALYSIS_FAIL", new_doc.filename)
        db.session.commit()
        return jsonify({"error": f"AI model configuration error: {e}"}), 500
    except Exception as e: # Catch any other general exceptions during content generation
        print(f"An error occurred during Gemini API call: {e}")
        new_doc.status = 'Analysis Failed'
        new_doc.summary = f"Analysis failed: {e}"
        log_event("ANALYSIS_FAIL", new_doc.filename)
        db.session.commit()
        return jsonify({"error": "Failed to get a response from the AI model. Check server logs for details."}), 500

@app.route('/ask', methods=['POST'])
def ask_question():
    """Answers a follow-up question based on provided document context."""
    # The get_gemini_model will handle checks for API key availability.
    
    data = request.get_json()
    if not data or 'document_text' not in data or 'question' not in data:
        return jsonify({"error": "Missing document_text or question in request."}), 400

    # Get selected model from the request JSON, default to 'gemini-1.5-flash'
    selected_model_name = data.get('model', 'gemini-1.5-flash')

    qa_prompt = _build_qa_prompt(data['document_text'], data['question'])
    
    try:
        # Get the dynamically selected model for the chat
        model_instance = get_gemini_model(selected_model_name)
        
        chat = model_instance.start_chat(history=[
            {"role": "user", "parts": [f"Here is the legal document for context:\n\n{data['document_text']}"]},
            {"role": "model", "parts": ["Understood. I have the document context."]}
        ])
        
        response = chat.send_message(qa_prompt) # Use qa_prompt here, not question directly
        return jsonify({"answer": response.text})
    except ValueError as e: # Catch ValueError specifically for API key/model issues from get_gemini_model
        print(f"Gemini API initialization error for /ask: {e}")
        return jsonify({"error": f"AI model configuration error for chat: {e}"}), 500
    except Exception as e: # Catch any other general exceptions during chat generation
        print(f"An error occurred during /ask API call: {e}")
        return jsonify({"error": "Failed to get a response for your question. Check server logs for details."}), 500

@app.route('/documents', methods=['GET'])
def get_documents():
    """Retrieves all documents from the database."""
    documents = Document.query.order_by(Document.upload_date.desc()).all()
    return jsonify([doc.to_dict() for doc in documents])

@app.route('/history', methods=['GET'])
def get_history():
    """Retrieves all history events from the database."""
    events = HistoryEvent.query.order_by(HistoryEvent.timestamp.desc()).all()
    return jsonify([event.to_dict() for event in events])

@app.route('/document/<int:doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    """Deletes a document from the database."""
    doc = Document.query.get_or_404(doc_id)
    db.session.delete(doc)
    db.session.commit()
    log_event("DELETE_DOCUMENT", doc.filename)
    return jsonify({"message": "Document deleted successfully."})


# --- APPLICATION RUNNER ---

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000, threaded=False)
# LegalMind AI ⚖️🇮🇳

Your AI-powered legal co-pilot for demystifying Indian legal documents.

> A prototype developed for the Gen AI Exchange Hackathon.

## 📜 Project Description

In India, navigating complex legal documents is a significant challenge for the average person and small businesses, often leading to misunderstandings and exposure to financial and legal risks. LegalMind AI is an innovative web application designed to democratize access to legal understanding. Powered by **Google Gemini 1.5**, it provides an intuitive platform for users to upload legal PDFs and receive a clear, structured analysis and the ability to ask follow-up questions, all within the specific context of Indian law.

## ✨ Key Features

  * **Secure PDF Upload & Analysis:** Seamlessly upload PDF legal documents for processing.
  * **AI-Powered Summarization:** Get structured, easy-to-understand summaries tailored to the Indian legal framework.
  * **Interactive Q&A:** Ask specific follow-up questions and receive contextual answers about your document.
  * **Dynamic Keyword Highlighting:** Critical and moderate legal terms are automatically highlighted for quick risk assessment.
  * **Document & History Management:** Securely view, manage, and delete your analyzed documents and see a full timeline of your activity.
  * **Dynamic Model Selection:** Choose between the powerful **Gemini 1.5 Pro** for deep analysis or the fast **Gemini 1.5 Flash** for quick summaries.

## ⚙️ Technology Stack

  * **Frontend:** HTML5, CSS3, Vanilla JavaScript, `marked.js`
  * **Backend:** Python 3, Flask
  * **Database:** SQLite (via Flask-SQLAlchemy)
  * **AI Model:** Google Gemini 1.5 Pro & Flash
  * **PDF Processing:** PyPDF2

-----

## 🚀 How to Run Locally

Follow these instructions to get a local copy up and running for development and testing purposes.

### Prerequisites

  * Python 3.10+
  * Git
  * A Google Gemini API Key
  * Web browser (Chrome, Firefox, Edge, etc.)

### Installation & Setup

1.  **Clone the repository:**
    Open your terminal or command prompt and run:
    ```bash
    git clone [https://github.com/Krish2786/LegalMind-AI.git](https://github.com/Krish2786/LegalMind-AI.git)
    cd LegalMind-AI
    ```

2.  **Set up the Backend:**
    Navigate into the `backend` folder and set up your Python environment:
    ```bash
    cd backend

    # Create a Python virtual environment
    python -m venv venv

    # Activate the virtual environment
    # On Windows (PowerShell):
    .\venv\Scripts\Activate.ps1
    # On macOS/Linux (Bash/Zsh):
    # source venv/bin/activate

    # Install the required Python packages
    pip install -r requirements.txt
    ```

3.  **🔐 Configure Environment Variables (CRUCIAL STEP)**
    You need to provide your Google Gemini API key.
      * Create a new file named `.env` inside the `backend` folder.
      * Open the `.env` file and add your Google Gemini API key exactly as shown below:
        ```
        GOOGLE_API_KEY="your_gemini_api_key_here"
        ```
        Replace `"your_gemini_api_key_here"` with your actual API key.

4.  **Run the Application:**
    You will need **two separate terminal windows** running simultaneously: one for the backend server and one for the frontend server.

      * **Terminal 1: Start the Backend Server**
        (Ensure you are in the `backend` folder and your `venv` is activated from step 2)
        ```bash
        python app.py
        ```
        The backend will start and typically run on `http://127.0.0.1:5000` or `http://localhost:5000`.

      * **Terminal 2: Start the Frontend Server**
        (Open a **new** terminal window)
        ```bash
        # Navigate to the frontend folder
        cd LegalMind-AI/frontend

        # Start a simple Python HTTP server to serve the frontend files
        python -m http.server 8000
        ```
        The frontend will be served from `http://localhost:8000`.

5.  **Access the Application:**
    Open your web browser and navigate to **`http://localhost:8000`** to interact with LegalMind AI.

-----

## 🔮 Future Plans

  * **Multilingual Support:** Extend analysis and summarization to various Indian languages (e.g., Hindi, Tamil).
  * **Comparative Analysis:** Allow users to upload two documents to have the AI compare them and highlight differences.
  * **Risk Scoring:** Implement a feature to provide a quantitative risk score (e.g., 7.5/10) for a quick assessment of a document's severity.
  * **User Accounts & Authentication:** Implement secure user login and profile management.
  * **Deployment to Cloud:** Deploy the application to a scalable cloud platform for wider accessibility

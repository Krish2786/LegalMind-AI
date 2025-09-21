document.addEventListener('DOMContentLoaded', function() {
    // --- ELEMENT REFERENCES ---
    const analysisForm = document.getElementById('analysis-form');
    const fileInput = document.getElementById('fileInput');
    const promptInput = document.getElementById('promptInput');
    const modelSelect = document.getElementById('modelSelect'); // New: Model selection
    const submitBtn = document.getElementById('submitBtn');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const uploadArea = document.getElementById('uploadArea');
    const fileNameDisplay = document.getElementById('fileName');
    const resultsContent = document.getElementById('results-content');
    const chatMessages = document.getElementById('chatMessages');
    const chatInput = document.getElementById('chatInput');
    const chatSendBtn = document.getElementById('chatSendBtn');
    
    let documentContext = "";
    let currentModel = modelSelect.value; // Initialize with default selected model

    // Listen for changes in the model selection
    modelSelect.addEventListener('change', () => {
        currentModel = modelSelect.value;
    });
    
    // --- KEYWORD LISTS & HIGHLIGHTING FUNCTION ---
    const criticalWords = ['terminate', 'termination', 'indemnify', 'indemnification', 'liability', 'breach', 'default', 'waive', 'arbitration', 'litigation', 'damages', 'unfavorable', 'without cause'];
    const moderateWords = ['insurance', 'confidentiality', 'notice period', 'payment terms', 'obligations', 'jurisdiction', 'governing law', 'assignment', 'exhibits'];

    function highlightKeywords(htmlContent) {
        let highlightedContent = htmlContent;
        criticalWords.forEach(word => {
            const regex = new RegExp(`\\b(${word})\\b`, 'gi');
            highlightedContent = highlightedContent.replace(regex, `<span class="highlight-critical">$1</span>`);
        });
        moderateWords.forEach(word => {
            const regex = new RegExp(`\\b(${word})\\b`, 'gi');
            highlightedContent = highlightedContent.replace(regex, `<span class="highlight-moderate">$1</span>`);
        });
        return highlightedContent;
    }
    
    // --- FUNCTION TO LOAD ANALYSIS FROM "VIEW" CLICK ---
    function loadAnalysisFromStorage() {
        const storedDoc = localStorage.getItem('viewAnalysis');
        if (storedDoc) {
            const doc = JSON.parse(storedDoc);
            
            fileNameDisplay.textContent = `Viewing analysis for: ${doc.filename}`;
            
            const rawHtml = marked.parse(doc.summary);
            const highlightedHtml = highlightKeywords(rawHtml);
            resultsContent.innerHTML = highlightedHtml;

            if (doc.full_text) {
                documentContext = doc.full_text;
                enableChat();
            } else {
                addMessage("Summary loaded, but Q&A is unavailable as its full text was not saved.", 'ai');
            }
            
            localStorage.removeItem('viewAnalysis');
        }
    }
    
    // --- FILE UPLOAD UI HANDLING ---
    uploadArea.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            fileNameDisplay.textContent = `Selected file: ${fileInput.files[0].name}`;
        }
    });
    
    // --- MAIN FORM SUBMISSION HANDLING ---
    analysisForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const file = fileInput.files[0];
        const prompt = promptInput.value;
        const selectedModel = modelSelect.value; // Get selected model here
        
        if (!file) {
            alert('Please select a PDF file to analyze.');
            return;
        }

        loadingOverlay.style.display = 'flex';
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-cogs fa-spin"></i> Analyzing...';
        resultsContent.innerHTML = ''; 

        const formData = new FormData();
        formData.append('pdfFile', file);
        formData.append('prompt', prompt);
        formData.append('model', selectedModel); // Add selected model to formData

        try {
            const response = await fetch('https://legalmind-ai-onrender.com/simplify', { // UPDATED HERE
                method: 'POST',
                body: formData,
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'An unknown error occurred.');
            
            documentContext = data.document_text;
            
            const rawHtml = marked.parse(data.summary);
            const highlightedHtml = highlightKeywords(rawHtml);
            resultsContent.innerHTML = highlightedHtml;

            enableChat();
        } catch (error) {
            console.error('Error:', error);
            resultsContent.innerHTML = `<p style="color: var(--accent);"><b>Error:</b> ${error.message}</p>`;
        } finally {
            loadingOverlay.style.display = 'none';
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-cogs"></i> Analyze Document';
        }
    });

    // --- CHAT FUNCTIONALITY ---
    function enableChat() {
        chatInput.disabled = false;
        chatSendBtn.disabled = false;
        chatMessages.innerHTML = '';
        addMessage("I've loaded the document. Ask me anything about it.", 'ai');
    }

    function addMessage(text, sender, isLoading = false) {
        const messageEl = document.createElement('div');
        messageEl.classList.add('message', sender);
        if (isLoading) {
            messageEl.innerHTML = '<div class="spinner-dots"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div>';
        } else {
            messageEl.textContent = text;
        }
        chatMessages.appendChild(messageEl);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return messageEl;
    }

    async function handleSendMessage() {
        const question = chatInput.value.trim();
        if (!question || !documentContext) return;

        addMessage(question, 'user');
        chatInput.value = '';
        const thinkingMessage = addMessage('', 'ai', true);

        try {
            const response = await fetch('https://legalmind-ai-onrender.com/ask', { // UPDATED HERE
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    document_text: documentContext,
                    question: question,
                    model: currentModel // Pass the current model selection to the chat API
                })
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error);
            
            thinkingMessage.classList.remove('loading');
            thinkingMessage.textContent = data.answer;

        } catch (error) {
            thinkingMessage.textContent = `Error: ${error.message}`;
            console.error("Chat error:", error);
        }
    }

    chatSendBtn.addEventListener('click', handleSendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleSendMessage();
        }
    });

    // --- RUN ON PAGE LOAD ---
    loadAnalysisFromStorage();
});

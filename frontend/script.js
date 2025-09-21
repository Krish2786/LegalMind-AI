document.addEventListener('DOMContentLoaded', () => {
    // --- 1. Get references to all the necessary HTML elements ---
    const uploadForm = document.getElementById('upload-form');
    const submitBtn = document.getElementById('submit-btn');
    const resultsSection = document.getElementById('results-section');
    const resultsContent = document.getElementById('results-content');
    const loadingSpinner = document.getElementById('loading-spinner');
    const pdfFileInput = document.getElementById('pdf-file');

    // --- 2. Add a 'submit' event listener to the form ---
    uploadForm.addEventListener('submit', async (event) => {
        // Prevent the default browser action of reloading the page on form submission
        event.preventDefault();

        // Get the actual file object and the text from the input fields
        const pdfFile = pdfFileInput.files[0];
        const promptText = document.getElementById('prompt').value;
        
        // Basic validation to ensure a file is selected
        if (!pdfFile) {
            alert('Please select a PDF file to upload.');
            return;
        }

        // --- 3. Update the UI to show a loading state ---
        submitBtn.disabled = true;
        submitBtn.textContent = 'Analyzing...';
        resultsSection.classList.remove('hidden'); // Show the results area
        loadingSpinner.classList.remove('hidden'); // Show the spinning loader
        resultsContent.innerHTML = ''; // Clear any previous results

        // --- 4. Prepare the data for sending ---
        // FormData is the modern way to send files and text to a server
        const formData = new FormData();
        formData.append('pdfFile', pdfFile);
        formData.append('prompt', promptText);

        try {
            // --- 5. Send the data to the backend API using fetch() ---
            // This URL must match where your Python Flask server is running
            const response = await fetch('http://127.0.0.1:5000/simplify', {
                method: 'POST',
                body: formData, // The FormData object is sent as the request body
            });

            // Parse the JSON response from the server
            const data = await response.json();

            // Handle potential errors returned from the server (e.g., bad PDF)
            if (!response.ok) {
                throw new Error(data.error || 'Something went wrong on the server.');
            }
            
            // --- 6. Display the successful result ---
            resultsContent.textContent = data.summary;

        } catch (error) {
            // --- 7. Display any network or server errors ---
            console.error('Error:', error);
            resultsContent.textContent = `An error occurred: ${error.message}`;
        } finally {
            // --- 8. Reset the UI, whether it succeeded or failed ---
            loadingSpinner.classList.add('hidden'); // Hide the loader
            submitBtn.disabled = false; // Re-enable the button
            submitBtn.textContent = 'Simplify Document';
        }
    });
});
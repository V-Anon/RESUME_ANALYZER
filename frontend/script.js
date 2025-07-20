document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('resume-form');
    const submitBtn = document.getElementById('submit-btn');
    const fileInput = document.getElementById('resume-file-input');
    const fileNameDisplay = document.getElementById('file-name-display');
    const resultContainer = document.getElementById('result-container');
    const responseOutput = document.getElementById('response-output');
    const loader = document.getElementById('loader');

    // Display the selected file name
    fileInput.addEventListener('change', () => {
        fileNameDisplay.textContent = fileInput.files.length > 0 ? fileInput.files[0].name : '';
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        // 1. Get form data
        const formData = new FormData(form);
        const resumeFile = formData.get('resume');
        const jobDescription = formData.get('jobDescription');

        // 2. Basic validation
        if (!resumeFile || resumeFile.size === 0) {
            alert('Please upload a resume file.');
            return;
        }
        if (!jobDescription.trim()) {
            alert('Please enter a job description.');
            return;
        }

        // 3. Prepare UI for loading
        submitBtn.disabled = true;
        submitBtn.textContent = 'Analyzing...';
        resultContainer.classList.remove('hidden');
        responseOutput.innerHTML = '';
        responseOutput.classList.remove('error');
        loader.classList.remove('hidden');

        try {
            // 4. Send data to the backend
            const response = await fetch('/analyze', {
                method: 'POST',
                body: formData,
            });

            const result = await response.json();

            // 5. Handle the response
            if (!response.ok) {
                // If we get an error from the server (e.g., 400, 500)
                throw new Error(result.error || `Server responded with status: ${response.status}`);
            }
            
            responseOutput.textContent = result.response;

        } catch (error) {
            // Handle network errors or errors thrown from the response handling
            responseOutput.textContent = `An error occurred: ${error.message}`;
            responseOutput.classList.add('error');
        } finally {
            // 6. Reset UI after completion
            loader.classList.add('hidden');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Analyze Now';
        }
    });
});
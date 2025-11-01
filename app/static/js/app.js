document.addEventListener('DOMContentLoaded', function() {
    const uploadBox = document.getElementById('uploadBox');
    const fileInput = document.getElementById('fileInput');
    const uploadSection = document.getElementById('uploadSection');
    const processingSection = document.getElementById('processingSection');
    const resultSection = document.getElementById('resultSection');
    const errorSection = document.getElementById('errorSection');
    const downloadBtn = document.getElementById('downloadBtn');
    const newConversionBtn = document.getElementById('newConversionBtn');
    const retryBtn = document.getElementById('retryBtn');
    const resultInfo = document.getElementById('resultInfo');
    const errorMessage = document.getElementById('errorMessage');

    let currentFilename = '';

    // Click to upload
    uploadBox.addEventListener('click', () => {
        fileInput.click();
    });

    // File selection
    fileInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });

    // Drag and drop
    uploadBox.addEventListener('dragover', function(e) {
        e.preventDefault();
        uploadBox.classList.add('drag-over');
    });

    uploadBox.addEventListener('dragleave', function(e) {
        e.preventDefault();
        uploadBox.classList.remove('drag-over');
    });

    uploadBox.addEventListener('drop', function(e) {
        e.preventDefault();
        uploadBox.classList.remove('drag-over');
        
        if (e.dataTransfer.files.length > 0) {
            handleFile(e.dataTransfer.files[0]);
        }
    });

    // Handle file upload
    function handleFile(file) {
        // Validate file type
        const validExtensions = ['mbox', 'mbx'];
        const fileExtension = file.name.split('.').pop().toLowerCase();
        
        if (!validExtensions.includes(fileExtension)) {
            showError('Invalid file type. Please upload an MBOX file (.mbox or .mbx)');
            return;
        }

        // Validate file size (50MB)
        const maxSize = 50 * 1024 * 1024;
        if (file.size > maxSize) {
            showError('File is too large. Maximum size is 50MB');
            return;
        }

        // Upload file
        uploadFile(file);
    }

    // Upload file to server
    function uploadFile(file) {
        showProcessing();

        const formData = new FormData();
        formData.append('file', file);

        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showError(data.error);
            } else {
                currentFilename = data.filename;
                showResult(data.email_count);
            }
        })
        .catch(error => {
            showError('Network error: ' + error.message);
        });
    }

    // Show processing state
    function showProcessing() {
        uploadSection.style.display = 'none';
        processingSection.style.display = 'block';
        resultSection.style.display = 'none';
        errorSection.style.display = 'none';
    }

    // Show result
    function showResult(emailCount) {
        uploadSection.style.display = 'none';
        processingSection.style.display = 'none';
        resultSection.style.display = 'block';
        errorSection.style.display = 'none';

        resultInfo.textContent = `Successfully converted ${emailCount} email${emailCount !== 1 ? 's' : ''} to PDF`;
    }

    // Show error
    function showError(message) {
        uploadSection.style.display = 'none';
        processingSection.style.display = 'none';
        resultSection.style.display = 'none';
        errorSection.style.display = 'block';

        errorMessage.textContent = message;
    }

    // Download button handler
    downloadBtn.addEventListener('click', function() {
        if (currentFilename) {
            window.location.href = '/download/' + encodeURIComponent(currentFilename);
        }
    });

    // New conversion button handler
    newConversionBtn.addEventListener('click', function() {
        resetApp();
    });

    // Retry button handler
    retryBtn.addEventListener('click', function() {
        resetApp();
    });

    // Reset application
    function resetApp() {
        uploadSection.style.display = 'block';
        processingSection.style.display = 'none';
        resultSection.style.display = 'none';
        errorSection.style.display = 'none';
        fileInput.value = '';
        currentFilename = '';
    }
});

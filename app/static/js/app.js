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

    // Settings panel elements
    const settingsBtn = document.getElementById('settingsBtn');
    const settingsOverlay = document.getElementById('settingsOverlay');
    const closeSettingsBtn = document.getElementById('closeSettingsBtn');
    const saveSettingsBtn = document.getElementById('saveSettingsBtn');
    const pageSizeSelect = document.getElementById('pageSize');
    const separatePDFsCheckbox = document.getElementById('separatePDFs');
    const includeAttachmentsCheckbox = document.getElementById('includeAttachments');
    const darkModeCheckbox = document.getElementById('darkMode');

    let currentFilename = '';

    // Initialize settings from localStorage
    initializeSettings();

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

        // Upload file
        uploadFile(file);
    }

    // Upload file to server
    function uploadFile(file) {
        showProcessing();

        const formData = new FormData();
        formData.append('file', file);

        // Get current settings and send with upload
        const settings = getSettings();
        formData.append('settings', JSON.stringify(settings));

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
                const separateMsg = data.separate_pdfs ? ' (as separate PDFs)' : '';
                showResult(data.email_count, separateMsg);
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
    function showResult(emailCount, extraMessage = '') {
        uploadSection.style.display = 'none';
        processingSection.style.display = 'none';
        resultSection.style.display = 'block';
        errorSection.style.display = 'none';

        resultInfo.textContent = `Successfully converted ${emailCount} email${emailCount !== 1 ? 's' : ''} to PDF${extraMessage}`;
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

    // Settings Panel Functions
    function initializeSettings() {
        // Load settings from localStorage
        const settings = getSettings();

        if (settings.pageSize) {
            pageSizeSelect.value = settings.pageSize;
        }
        if (settings.separatePDFs !== undefined) {
            separatePDFsCheckbox.checked = settings.separatePDFs;
        }
        if (settings.includeAttachments !== undefined) {
            includeAttachmentsCheckbox.checked = settings.includeAttachments;
        }
        if (settings.darkMode !== undefined) {
            darkModeCheckbox.checked = settings.darkMode;
        }
    }

    function getSettings() {
        const savedSettings = localStorage.getItem('mboxConverterSettings');
        return savedSettings ? JSON.parse(savedSettings) : {
            pageSize: 'A4',
            separatePDFs: false,
            includeAttachments: true,
            darkMode: false
        };
    }

    function saveSettings() {
        const settings = {
            pageSize: pageSizeSelect.value,
            separatePDFs: separatePDFsCheckbox.checked,
            includeAttachments: includeAttachmentsCheckbox.checked,
            darkMode: darkModeCheckbox.checked
        };

        localStorage.setItem('mboxConverterSettings', JSON.stringify(settings));
        return settings;
    }

    // Open settings panel
    settingsBtn.addEventListener('click', function() {
        settingsOverlay.classList.add('active');
    });

    // Close settings panel
    closeSettingsBtn.addEventListener('click', function() {
        settingsOverlay.classList.remove('active');
    });

    // Close settings when clicking outside the panel
    settingsOverlay.addEventListener('click', function(e) {
        if (e.target === settingsOverlay) {
            settingsOverlay.classList.remove('active');
        }
    });

    // Save settings button
    saveSettingsBtn.addEventListener('click', function() {
        const settings = saveSettings();

        // Show a brief confirmation (you can enhance this with a toast notification)
        const originalText = saveSettingsBtn.textContent;
        saveSettingsBtn.textContent = 'Settings Saved!';
        saveSettingsBtn.style.background = '#10b981';

        setTimeout(function() {
            saveSettingsBtn.textContent = originalText;
            saveSettingsBtn.style.background = '';
            settingsOverlay.classList.remove('active');
        }, 1000);
    });

    // Close settings panel with Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && settingsOverlay.classList.contains('active')) {
            settingsOverlay.classList.remove('active');
        }
    });
});

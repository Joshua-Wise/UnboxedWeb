document.addEventListener('DOMContentLoaded', function() {
    const uploadBox = document.getElementById('uploadBox');
    const fileInput = document.getElementById('fileInput');
    const uploadSection = document.getElementById('uploadSection');
    const processingSection = document.getElementById('processingSection');
    const processingText = document.getElementById('processingText');
    const resultSection = document.getElementById('resultSection');
    const errorSection = document.getElementById('errorSection');
    const downloadBtn = document.getElementById('downloadBtn');
    const newConversionBtn = document.getElementById('newConversionBtn');
    const retryBtn = document.getElementById('retryBtn');
    const resultInfo = document.getElementById('resultInfo');
    const errorMessage = document.getElementById('errorMessage');
    const selectedFilesDiv = document.getElementById('selectedFiles');
    const fileList = document.getElementById('fileList');
    const processFilesBtn = document.getElementById('processFilesBtn');

    // Settings panel elements
    const settingsBtn = document.getElementById('settingsBtn');
    const settingsOverlay = document.getElementById('settingsOverlay');
    const closeSettingsBtn = document.getElementById('closeSettingsBtn');
    const saveSettingsBtn = document.getElementById('saveSettingsBtn');
    const separatePDFsCheckbox = document.getElementById('separatePDFs');
    const includeAttachmentsCheckbox = document.getElementById('includeAttachments');
    const separateAttachmentsZipCheckbox = document.getElementById('separateAttachmentsZip');

    // Naming options elements
    const namingOptions = document.getElementById('namingOptions');
    const namingItemsList = document.getElementById('namingItemsList');
    const namingPreview = document.getElementById('namingPreview');

    // Default naming items configuration
    let namingItems = [
        { id: 'subject', label: 'Subject', enabled: true },
        { id: 'date', label: 'Date', enabled: false },
        { id: 'sender', label: 'Sender', enabled: false }
    ];

    let currentFilename = '';
    let selectedFiles = [];

    // Initialize settings from localStorage
    initializeSettings();

    // Render naming items list initially
    renderNamingItems();

    // Toggle naming options visibility when separatePDFs checkbox changes
    separatePDFsCheckbox.addEventListener('change', function() {
        namingOptions.style.display = separatePDFsCheckbox.checked ? 'block' : 'none';
    });

    // Click to upload
    uploadBox.addEventListener('click', () => {
        fileInput.click();
    });

    // File selection
    fileInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            handleFiles(Array.from(e.target.files));
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
            handleFiles(Array.from(e.dataTransfer.files));
        }
    });

    // Handle multiple files
    function handleFiles(files) {
        // Validate all files
        const validExtensions = ['mbox', 'mbx'];
        const invalidFiles = [];

        for (const file of files) {
            const fileExtension = file.name.split('.').pop().toLowerCase();
            if (!validExtensions.includes(fileExtension)) {
                invalidFiles.push(file.name);
            }
        }

        if (invalidFiles.length > 0) {
            showError(`Invalid file type(s): ${invalidFiles.join(', ')}. Please upload only MBOX files (.mbox or .mbx)`);
            return;
        }

        // Store selected files
        selectedFiles = files;

        // Display selected files
        displaySelectedFiles();
    }

    // Display selected files list
    function displaySelectedFiles() {
        fileList.innerHTML = '';

        selectedFiles.forEach((file, index) => {
            const li = document.createElement('li');
            li.style.cssText = 'padding: 8px; background: #f5f5f5; margin-bottom: 4px; border-radius: 4px; display: flex; justify-content: space-between; align-items: center;';

            const fileInfo = document.createElement('span');
            fileInfo.textContent = `${file.name} (${formatFileSize(file.size)})`;

            const removeBtn = document.createElement('button');
            removeBtn.innerHTML = '<i class="fas fa-times"></i>';
            removeBtn.style.cssText = 'background: #dc3545; color: white; border: none; border-radius: 4px; padding: 6px 10px; cursor: pointer; transition: all 0.2s;';
            removeBtn.addEventListener('mouseenter', function() {
                this.style.background = '#c82333';
            });
            removeBtn.addEventListener('mouseleave', function() {
                this.style.background = '#dc3545';
            });
            removeBtn.addEventListener('click', function() {
                selectedFiles.splice(index, 1);
                if (selectedFiles.length === 0) {
                    selectedFilesDiv.style.display = 'none';
                    uploadBox.style.display = 'block';
                } else {
                    displaySelectedFiles();
                }
            });

            li.appendChild(fileInfo);
            li.appendChild(removeBtn);
            fileList.appendChild(li);
        });

        // Show the selected files section
        selectedFilesDiv.style.display = 'block';
        uploadBox.style.display = 'none';
    }

    // Format file size for display
    function formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }

    // Process files button handler
    processFilesBtn.addEventListener('click', function() {
        if (selectedFiles.length > 0) {
            uploadFiles(selectedFiles);
        }
    });

    // Upload files to server
    function uploadFiles(files) {
        showProcessing();

        // Update processing text based on file count
        processingText.textContent = files.length === 1
            ? 'Processing your MBOX file...'
            : `Processing ${files.length} MBOX files...`;

        const formData = new FormData();

        // Append all files
        files.forEach(file => {
            formData.append('files', file);
        });

        // Get current settings and send with upload
        const settings = getSettings();

        // Convert namingItems array to format expected by backend
        settings.naming = {
            items: namingItems.map(item => ({
                id: item.id,
                enabled: item.enabled
            }))
        };

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
                const fileCountMsg = files.length > 1 ? ` from ${files.length} files` : '';
                const separateMsg = data.separate_pdfs ? ' (as separate PDFs)' : '';
                const attachmentsMsg = data.attachments_zip ? `\n\nNon-text attachments saved to: ${data.attachments_zip} (${data.attachment_count} files)` : '';
                showResult(data.email_count, fileCountMsg + separateMsg + attachmentsMsg);
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
        selectedFilesDiv.style.display = 'none';
        uploadBox.style.display = 'block';
        processingSection.style.display = 'none';
        resultSection.style.display = 'none';
        errorSection.style.display = 'none';
        fileInput.value = '';
        currentFilename = '';
        selectedFiles = [];
        fileList.innerHTML = '';
    }

    // Naming Items Functions
    function renderNamingItems() {
        namingItemsList.innerHTML = '';

        namingItems.forEach((item, index) => {
            const itemDiv = document.createElement('div');
            itemDiv.style.cssText = 'display: flex; align-items: center; padding: 8px; margin-bottom: 4px; background: white; border-radius: 4px; gap: 8px;';

            // Checkbox
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = `naming-${item.id}`;
            checkbox.checked = item.enabled;
            checkbox.style.marginRight = '8px';
            checkbox.addEventListener('change', function() {
                namingItems[index].enabled = this.checked;
                updateNamingPreview();
            });

            // Label
            const label = document.createElement('label');
            label.htmlFor = `naming-${item.id}`;
            label.textContent = item.label;
            label.style.cssText = 'flex: 1; cursor: pointer;';

            // Buttons container
            const buttonsDiv = document.createElement('div');
            buttonsDiv.style.cssText = 'display: flex; gap: 4px;';

            // Up button
            const upButton = document.createElement('button');
            upButton.innerHTML = '↑';
            upButton.type = 'button';
            upButton.style.cssText = 'padding: 4px 10px; border: 1px solid #ccc; background: white; border-radius: 3px; cursor: pointer; font-size: 14px;';
            upButton.disabled = index === 0;
            if (index === 0) upButton.style.opacity = '0.3';
            upButton.addEventListener('click', function() {
                moveNamingItem(index, -1);
            });

            // Down button
            const downButton = document.createElement('button');
            downButton.innerHTML = '↓';
            downButton.type = 'button';
            downButton.style.cssText = 'padding: 4px 10px; border: 1px solid #ccc; background: white; border-radius: 3px; cursor: pointer; font-size: 14px;';
            downButton.disabled = index === namingItems.length - 1;
            if (index === namingItems.length - 1) downButton.style.opacity = '0.3';
            downButton.addEventListener('click', function() {
                moveNamingItem(index, 1);
            });

            buttonsDiv.appendChild(upButton);
            buttonsDiv.appendChild(downButton);

            itemDiv.appendChild(checkbox);
            itemDiv.appendChild(label);
            itemDiv.appendChild(buttonsDiv);

            namingItemsList.appendChild(itemDiv);
        });

        updateNamingPreview();
    }

    function moveNamingItem(index, direction) {
        const newIndex = index + direction;
        if (newIndex < 0 || newIndex >= namingItems.length) return;

        // Swap items
        const temp = namingItems[index];
        namingItems[index] = namingItems[newIndex];
        namingItems[newIndex] = temp;

        renderNamingItems();
    }

    function updateNamingPreview() {
        const parts = ['000001'];

        namingItems.forEach(item => {
            if (item.enabled) {
                if (item.id === 'subject') {
                    parts.push('Subject');
                } else if (item.id === 'date') {
                    parts.push('2024-01-15');
                } else if (item.id === 'sender') {
                    parts.push('sender@example.com');
                }
            }
        });

        const preview = parts.join('_') + '.pdf';
        namingPreview.textContent = 'Preview: ' + preview;
    }

    // Settings Panel Functions
    function initializeSettings() {
        // Load settings from localStorage
        const settings = getSettings();

        if (settings.separatePDFs !== undefined) {
            separatePDFsCheckbox.checked = settings.separatePDFs;
            // Show/hide naming options based on saved setting
            namingOptions.style.display = settings.separatePDFs ? 'block' : 'none';
        }
        if (settings.includeAttachments !== undefined) {
            includeAttachmentsCheckbox.checked = settings.includeAttachments;
        }
        if (settings.separateAttachmentsZip !== undefined) {
            separateAttachmentsZipCheckbox.checked = settings.separateAttachmentsZip;
        }
        // Initialize naming items
        if (settings.namingItems && Array.isArray(settings.namingItems)) {
            namingItems = settings.namingItems;
            renderNamingItems();
        }
    }

    function getSettings() {
        const savedSettings = localStorage.getItem('mboxConverterSettings');
        return savedSettings ? JSON.parse(savedSettings) : {
            pageSize: 'Letter',
            separatePDFs: false,
            includeAttachments: true,
            separateAttachmentsZip: false,
            namingItems: [
                { id: 'subject', label: 'Subject', enabled: true },
                { id: 'date', label: 'Date', enabled: false },
                { id: 'sender', label: 'Sender', enabled: false }
            ]
        };
    }

    function saveSettings() {
        const settings = {
            pageSize: 'Letter',  // Default to Letter
            separatePDFs: separatePDFsCheckbox.checked,
            includeAttachments: includeAttachmentsCheckbox.checked,
            separateAttachmentsZip: separateAttachmentsZipCheckbox.checked,
            namingItems: namingItems
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

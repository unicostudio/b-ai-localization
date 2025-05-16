// Game Localization Tool - Client-side version
document.addEventListener('DOMContentLoaded', function() {
    // Global variables
    let csvData = null;
    let uploadedImages = [];
    let processingQueue = [];
    let processedCount = 0;
    let characterData = null;
    let customCharacterData = null;
    let visionModel = 'openai/chatgpt-4o-latest';
    
    // Default character data
    characterData = {
        "turkish": {
            "Lily": "Bediş",
            "Granny Amy": "Babaanne Ayşe",
            "Uncle Bubba": "Bubba Amca",
            "Poppy": "Bibi"
        },
        "french": {
            "Lily": "Lili",
            "Granny Amy": "Mamie Amy",
            "Uncle Bubba": "Oncle Bubba",
            "Poppy": "Papi"
        },
        "german": {
            "Lily": "Lilly",
            "Granny Amy": "Oma Amy",
            "Uncle Bubba": "Onkel Bubba",
            "Poppy": "Poppy"
        }
    };
    
    try {
        const charDataElement = document.getElementById('characterData');
        if (charDataElement) {
            const extraCharData = JSON.parse(charDataElement.textContent);
            // Merge with default data
            characterData = {...characterData, ...extraCharData};
            console.log('Additional character data loaded successfully');
        }
    } catch (e) {
        console.error('Error loading additional character data:', e);
    }
    
    // Initialize game prompts
    const gamePrompts = {
        'brain-test-1': `You are a game localization translator expert.

You have been provided with English text from a 'Brain Test' puzzle game.
You can use the following information for localization:
    
    You're localizing a 'Brain Test' named children's brain teaser game that uses word play,
    Brain Test is a children's brain teaser game that is popular worldwide, known for its tricky and often unexpected brain teasers.
    
    IMPORTANT NOTE: DO NOT translate any character names in the text. Keep all character names as they are in English.
    Character names like Lily, Granny Amy, Uncle Bubba, etc. should remain unchanged in your translation.
    These will be replaced with the proper localized names in a separate step.`,
        
        'brain-test-2': `You are a game localization translator expert.

You have been provided with English text from 'Brain Test 2: Tricky Stories'.
You can use the following information for localization:
    
    You're localizing a puzzle game that uses word play and tricky storylines,
    Brain Test 2 features more complex scenarios with characters and storylines.
    
    IMPORTANT NOTE: DO NOT translate any character names in the text. Keep all character names as they are in English.
    Character names like Lily, Granny Amy, Uncle Bubba, etc. should remain unchanged in your translation.
    These will be replaced with the proper localized names in a separate step.`,
        
        'brain-test-3': `You are a game localization translator expert.

You have been provided with English text from 'Brain Test 3: Tricky Quests'.
You can use the following information for localization:
    
    You're localizing a puzzle game with more adventure elements,
    Brain Test 3 incorporates quest-like puzzles and more complex gameplay.
    
    IMPORTANT NOTE: DO NOT translate any character names in the text. Keep all character names as they are in English.
    Character names like Lily, Granny Amy, Uncle Bubba, etc. should remain unchanged in your translation.
    These will be replaced with the proper localized names in a separate step.`,
        
        'brain-test-4': `You are a game localization translator expert.

You have been provided with English text from 'Brain Test 4: Crime Series'.
You can use the following information for localization:
    
    You're localizing a puzzle game with crime and mystery themes,
    Brain Test 4 has detective-like puzzles and crime-solving scenarios.
    
    IMPORTANT NOTE: DO NOT translate any character names in the text. Keep all character names as they are in English.
    Character names like Lily, Granny Amy, Uncle Bubba, etc. should remain unchanged in your translation.
    These will be replaced with the proper localized names in a separate step.`
    };
    
    // Navigation buttons
    document.getElementById('goToStep2').addEventListener('click', () => {
        if (validateCsvFile()) {
            showTab('step2-tab');
        }
    });
    
    document.getElementById('backToStep1').addEventListener('click', () => {
        showTab('step1-tab');
    });
    
    document.getElementById('goToStep3').addEventListener('click', () => {
        if (validateApiKey()) {
            showTab('step3-tab');
        }
    });
    
    document.getElementById('backToStep2').addEventListener('click', () => {
        showTab('step2-tab');
    });
    
    document.getElementById('goToStep4').addEventListener('click', () => {
        updateSettingsSummary();
        showTab('step4-tab');
    });
    
    document.getElementById('backToStep3').addEventListener('click', () => {
        showTab('step3-tab');
    });
    
    // Game selection affects prompt
    document.getElementById('gameSelect').addEventListener('change', function() {
        const gameValue = this.value;
        const customPromptElem = document.getElementById('customPrompt');
        
        if (gameValue !== 'custom' && gamePrompts[gameValue]) {
            customPromptElem.value = gamePrompts[gameValue];
        } else if (gameValue === 'custom') {
            // Leave the current prompt as is for editing
        }
    });
    
    // Start processing button
    document.getElementById('startProcessing').addEventListener('click', startProcessing);
    
    // Download JSON button
    document.getElementById('downloadJson').addEventListener('click', downloadJson);
    
    // File handling
    document.getElementById('csvFile').addEventListener('change', handleCsvFileSelect);
    document.getElementById('imageFolder').addEventListener('change', handleImageFolderSelect);
    document.getElementById('charFile').addEventListener('change', handleCharFileSelect);
    
    // API Key handling
    document.getElementById('apiKey').addEventListener('change', function() {
        localStorage.setItem('openrouter_api_key', this.value);
    });
    
    // Load API key from storage if available
    const savedApiKey = localStorage.getItem('openrouter_api_key');
    if (savedApiKey) {
        document.getElementById('apiKey').value = savedApiKey;
    }
    
    // Helper functions
    function showTab(tabId) {
        // For Bootstrap 5, we need to select the tab element properly
        // Make sure it selects the actual tab trigger element, not the tab pane
        const tabElement = document.querySelector(`#${tabId}`);
        if (tabElement) {
            const tab = new bootstrap.Tab(tabElement);
            tab.show();
            console.log(`Showing tab: ${tabId}`);
        } else {
            console.error(`Tab element not found: ${tabId}`);
            // Fallback method using direct class manipulation if bootstrap.Tab fails
            try {
                // Hide all tab panes
                document.querySelectorAll('.tab-pane').forEach(pane => {
                    pane.classList.remove('show', 'active');
                });
                
                // Hide all tab buttons
                document.querySelectorAll('.nav-link').forEach(tab => {
                    tab.classList.remove('active');
                    tab.setAttribute('aria-selected', 'false');
                });
                
                // Show the selected tab pane
                const targetPane = document.querySelector(`#${tabId.replace('-tab', '')}`);
                if (targetPane) {
                    targetPane.classList.add('show', 'active');
                }
                
                // Activate the selected tab button
                const targetTab = document.querySelector(`#${tabId}`);
                if (targetTab) {
                    targetTab.classList.add('active');
                    targetTab.setAttribute('aria-selected', 'true');
                }
                
                console.log(`Manually activated tab: ${tabId}`);
            } catch (e) {
                console.error('Error in manual tab activation:', e);
            }
        }
    }
    
    function validateCsvFile() {
        // For testing purposes, allow proceeding even without CSV and images
        // Just show warnings instead of blocking
        if (!csvData) {
            console.warn('No CSV data loaded, but proceeding for testing');
            // Add a warning message instead of alert
            addStatusMessage('Warning: No CSV data loaded. This is allowed for testing but will need data eventually.', 'warning');
        }
        
        if (uploadedImages.length === 0) {
            console.warn('No images loaded, but proceeding for testing');
            // Add a warning message instead of alert
            addStatusMessage('Warning: No images loaded. This is allowed for testing but will need images eventually.', 'warning');
        }
        
        // Always return true for testing
        return true;
    }
    
    function validateApiKey() {
        const apiKey = document.getElementById('apiKey').value.trim();
        if (!apiKey) {
            alert('Please enter your OpenRouter API key.');
            return false;
        }
        return true;
    }
    
    function handleImageFolderSelect(event) {
        const files = event.target.files;
        if (!files || files.length === 0) return;
        
        // Clear previous images
        uploadedImages = [];
        
        // Filter for image files
        const imageTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
        const previewContainer = document.getElementById('imagePreview');
        previewContainer.innerHTML = '';
        
        let imageCount = 0;
        const previewCount = Math.min(files.length, 4); // Show up to 4 image previews
        
        // Process each file
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            
            // Check if it's an image
            if (imageTypes.includes(file.type) || file.name.match(/\.(jpg|jpeg|png|gif|webp)$/i)) {
                uploadedImages.push(file);
                
                // Create preview for the first few images
                if (imageCount < previewCount) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        const preview = document.createElement('img');
                        preview.src = e.target.result;
                        preview.style.maxHeight = '100px';
                        preview.style.maxWidth = '150px';
                        preview.className = 'me-2 mb-2';
                        preview.title = file.name;
                        previewContainer.appendChild(preview);
                    };
                    reader.readAsDataURL(file);
                    imageCount++;
                }
            }
        }
        
        // Add summary text
        const summaryDiv = document.createElement('div');
        summaryDiv.className = 'text-muted mt-2';
        summaryDiv.textContent = `Loaded ${uploadedImages.length} image files`;
        previewContainer.appendChild(summaryDiv);
        
        addStatusMessage(`Loaded ${uploadedImages.length} image files`, 'success');
    }
    
    function handleCharFileSelect(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        addStatusMessage('Reading character file...', 'info');
        
        const reader = new FileReader();
        reader.onload = function(e) {
            try {
                customCharacterData = JSON.parse(e.target.result);
                addStatusMessage(`Successfully loaded character data with ${Object.keys(customCharacterData).length} languages`, 'success');
                
                // Show preview
                const previewDiv = document.getElementById('charPreview');
                previewDiv.innerHTML = `<div class="alert alert-success">Character file loaded successfully with ${Object.keys(customCharacterData).length} languages</div>`;
                previewDiv.classList.remove('d-none');
            } catch (error) {
                addStatusMessage(`Error parsing character file: ${error.message}`, 'error');
                
                const previewDiv = document.getElementById('charPreview');
                previewDiv.innerHTML = `<div class="alert alert-danger">Error parsing character file: ${error.message}</div>`;
                previewDiv.classList.remove('d-none');
            }
        };
        
        reader.readAsText(file);
    }
    
    function handleCsvFileSelect(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        addStatusMessage('Reading CSV file...', 'info');
        
        Papa.parse(file, {
            header: true,
            skipEmptyLines: true,
            delimiter: ';', // Default delimiter
            complete: function(results) {
                if (results.errors.length > 0) {
                    // Try with comma delimiter if semicolon fails
                    Papa.parse(file, {
                        header: true,
                        skipEmptyLines: true,
                        delimiter: ',',
                        complete: handleParsedCsv,
                        error: function(error) {
                            addStatusMessage(`Error parsing CSV: ${error}`, 'error');
                        }
                    });
                } else {
                    handleParsedCsv(results);
                }
            },
            error: function(error) {
                addStatusMessage(`Error parsing CSV: ${error}`, 'error');
            }
        });
    }
    
    // Define the addStatusMessage function needed by validateCsvFile
    function addStatusMessage(message, type = 'info') {
        const statusLog = document.getElementById('statusLog');
        if (!statusLog) {
            console.log(`[${type.toUpperCase()}] ${message}`);
            return;
        }
        
        const timestamp = new Date().toLocaleTimeString();
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `status-item status-${type}`;
        messageDiv.innerHTML = `<span class="timestamp">[${timestamp}]</span> ${message}`;
        
        statusLog.appendChild(messageDiv);
        statusLog.scrollTop = statusLog.scrollHeight;
        
        console.log(`[${type.toUpperCase()}] ${message}`);
    }
});

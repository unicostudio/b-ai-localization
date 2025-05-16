// Game Localization Tool - Processing Functions

// Global variables for processing
let processingQueue = [];
let processedCount = 0;

// Function to handle main processing flow
function handleParsedCsv(results) {
    if (results.errors.length > 0) {
        addStatusMessage(`Error parsing CSV: ${results.errors[0].message}`, 'error');
        return;
    }
    
    // Validate required columns
    const requiredColumns = ['IDS', 'EN', 'LOCID'];
    const columns = results.meta.fields;
    const missingColumns = requiredColumns.filter(col => !columns.includes(col));
    
    if (missingColumns.length > 0) {
        addStatusMessage(`CSV is missing required columns: ${missingColumns.join(', ')}`, 'error');
        return;
    }
    
    csvData = results.data;
    addStatusMessage(`Successfully parsed CSV with ${csvData.length} entries`, 'success');
    
    // Show preview
    showCsvPreview(csvData);
}

function showCsvPreview(data) {
    const previewDiv = document.getElementById('csvPreview');
    if (data.length === 0) {
        previewDiv.innerHTML = '<div class="alert alert-warning">No data found in CSV file.</div>';
        return;
    }
    
    // Create a table for the preview
    let tableHtml = '<div class="table-wrapper"><table class="table table-sm table-striped table-responsive">';
    
    // Header row
    tableHtml += '<thead><tr>';
    const columns = Object.keys(data[0]);
    columns.forEach(column => {
        tableHtml += `<th>${column}</th>`;
    });
    tableHtml += '</tr></thead><tbody>';
    
    // Data rows (limit to 5 for preview)
    const previewData = data.slice(0, 5);
    previewData.forEach(row => {
        tableHtml += '<tr>';
        columns.forEach(column => {
            tableHtml += `<td>${row[column] || ''}</td>`;
        });
        tableHtml += '</tr>';
    });
    
    tableHtml += '</tbody></table></div>';
    
    if (data.length > 5) {
        tableHtml += `<div class="text-muted">Showing 5 of ${data.length} entries</div>`;
    }
    
    previewDiv.innerHTML = tableHtml;
}

function updateSettingsSummary() {
    const languages = [];
    if (document.getElementById('langTR').checked) languages.push('Turkish');
    if (document.getElementById('langFR').checked) languages.push('French');
    if (document.getElementById('langDE').checked) languages.push('German');
    if (document.getElementById('langES').checked) languages.push('Spanish');
    if (document.getElementById('langIT').checked) languages.push('Italian');
    if (document.getElementById('langPT').checked) languages.push('Portuguese');
    if (document.getElementById('langRU').checked) languages.push('Russian');
    if (document.getElementById('langJP').checked) languages.push('Japanese');
    if (document.getElementById('langKR').checked) languages.push('Korean');
    if (document.getElementById('langCN').checked) languages.push('Chinese');
    if (document.getElementById('langAR').checked) languages.push('Arabic');
    if (document.getElementById('langPL').checked) languages.push('Polish');
    
    const model = document.getElementById('modelSelect').options[document.getElementById('modelSelect').selectedIndex].text;
    const game = document.getElementById('gameSelect').options[document.getElementById('gameSelect').selectedIndex].text;
    
    let summary = `
        <ul>
            <li><strong>CSV File:</strong> ${document.getElementById('csvFile').files[0]?.name || 'None'}</li>
            <li><strong>Images:</strong> ${uploadedImages.length} files loaded</li>
            <li><strong>Character File:</strong> ${document.getElementById('charFile').files[0]?.name || 'Using default'}</li>
            <li><strong>Languages:</strong> ${languages.join(', ') || 'None selected'}</li>
            <li><strong>Model:</strong> ${model}</li>
            <li><strong>Game:</strong> ${game}</li>
            <li><strong>API Key:</strong> ${document.getElementById('apiKey').value ? 'Provided' : 'Missing'}</li>
            <li><strong>Entries to Process:</strong> ${csvData?.length || 0}</li>
        </ul>
    `;
    
    document.getElementById('settings-summary').innerHTML = summary;
}

function addStatusMessage(message, type = 'info') {
    const statusLog = document.getElementById('statusLog');
    const timestamp = new Date().toLocaleTimeString();
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `status-item status-${type}`;
    messageDiv.innerHTML = `<span class="timestamp">[${timestamp}]</span> ${message}`;
    
    statusLog.appendChild(messageDiv);
    statusLog.scrollTop = statusLog.scrollHeight;
    
    console.log(`[${type.toUpperCase()}] ${message}`);
}

function startProcessing() {
    console.log('Start Processing button clicked');
    
    // Validate requirements but allow testing with warning
    if (!csvData || csvData.length === 0) {
        addStatusMessage('Warning: No CSV data loaded. This is allowed for testing but will need data eventually.', 'warning');
        // Create dummy CSV data for testing
        csvData = [{IDS: 'ID1', EN: 'Test text', LOCID: 'TEST001'}];
    }
    
    // Get API key with fallback for testing
    let apiKey = document.getElementById('apiKey').value.trim();
    if (!apiKey) {
        addStatusMessage('Warning: No API key provided. Using test mode.', 'warning');
        apiKey = 'test-api-key';
    }
    
    // Get selected languages
    const languages = [];
    if (document.getElementById('langTR').checked) languages.push('TR');
    if (document.getElementById('langFR').checked) languages.push('FR');
    if (document.getElementById('langDE').checked) languages.push('DE');
    if (document.getElementById('langES').checked) languages.push('ES');
    if (document.getElementById('langIT').checked) languages.push('IT');
    if (document.getElementById('langPT').checked) languages.push('PT');
    if (document.getElementById('langRU').checked) languages.push('RU');
    if (document.getElementById('langJP').checked) languages.push('JP');
    if (document.getElementById('langKR').checked) languages.push('KR');
    if (document.getElementById('langCN').checked) languages.push('CN_TR');
    if (document.getElementById('langAR').checked) languages.push('AR');
    if (document.getElementById('langPL').checked) languages.push('PL');
    
    if (languages.length === 0) {
        addStatusMessage('Please select at least one language for translation.', 'error');
        return;
    }
    
    // Get model selection
    const modelKey = document.getElementById('modelSelect').value;
    // Convert model key to full OpenRouter model ID using the mapping from api.js
    // Accessing the global MODEL_IDS variable with window. prefix
    const model = window.MODEL_IDS[modelKey] || window.MODEL_IDS['gpt-4o']; // Default to GPT-4o if not found
    console.log(`Using model: ${modelKey} -> ${model}`);
    
    // Get custom prompt
    const customPrompt = document.getElementById('customPrompt').value;
    
    // Show progress UI
    document.getElementById('progressBar').classList.remove('d-none');
    document.getElementById('startProcessing').disabled = true;
    document.getElementById('results').classList.add('d-none');
    
    // Group data by image ID
    const imageGroups = {};
    csvData.forEach(row => {
        const imageId = row.IDS;
        if (!imageGroups[imageId]) {
            imageGroups[imageId] = [];
        }
        imageGroups[imageId].push(row);
    });
    
    // Prepare processing queue
    processingQueue = [];
    
    // Add default test data if no image groups
    if (Object.keys(imageGroups).length === 0) {
        addStatusMessage('Warning: No image groups found. Using test data.', 'warning');
        processingQueue.push({
            imageId: 'ID1',
            rows: [{IDS: 'ID1', EN: 'Test text 1', LOCID: 'TEST001'}]
        });
    } else {
        // Add real data
        Object.keys(imageGroups).forEach(imageId => {
            processingQueue.push({
                imageId: imageId,
                rows: imageGroups[imageId]
            });
        });
    }
    
    // If no uploaded images, create a dummy test image
    if (typeof uploadedImages === 'undefined' || uploadedImages.length === 0) {
        addStatusMessage('Warning: No images uploaded. Using placeholder image for testing.', 'warning');
        
        // Create a real Blob for test image to avoid FileReader errors
        const canvas = document.createElement('canvas');
        canvas.width = 100;
        canvas.height = 100;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, 100, 100);
        ctx.fillStyle = '#000000';
        ctx.font = '14px Arial';
        ctx.fillText('Test Image', 10, 50);
        
        // Convert canvas to blob
        canvas.toBlob(function(blob) {
            // Attach the blob to a File object
            const testImageFile = new File([blob], 'test1.jpg', {type: 'image/jpeg'});
            // Store in global uploadedImages
            window.uploadedImages = [testImageFile];
            console.log('Created test image blob:', testImageFile);
        }, 'image/jpeg');
        
        // Create a backup dummy object in case toBlob isn't supported
        if (!window.uploadedImages || window.uploadedImages.length === 0) {
            // Use a 1x1 transparent pixel as base64
            const b64Data = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=';
            const byteCharacters = atob(b64Data);
            const byteArrays = [];
            for (let i = 0; i < byteCharacters.length; i++) {
                byteArrays.push(byteCharacters.charCodeAt(i));
            }
            const byteArray = new Uint8Array(byteArrays);
            const blob = new Blob([byteArray], {type: 'image/png'});
            const testImageFile = new File([blob], 'test1.jpg', {type: 'image/jpeg'});
            window.uploadedImages = [testImageFile];
            console.log('Created fallback test image');
        }
    }
    
    // Reset processing state
    processedCount = 0;
    
    // Initialize results array
    const results = [];
    
    // Store total number of groups for progress tracking
    const totalGroups = processingQueue.length;
    
    addStatusMessage(`Starting to process ${totalGroups} image groups with ${languages.length} languages`, 'info');
    addStatusMessage(`Using model: ${model}`, 'info');
    
    // Process queue
    processNextGroup(apiKey, model, languages, customPrompt, results, totalGroups);
}

function processNextGroup(apiKey, model, languages, customPrompt, results, totalGroups) {
    if (processingQueue.length === 0) {
        // All done!
        finishProcessing(results);
        return;
    }
    
    const group = processingQueue.shift();
    const imageId = group.imageId;
    const rows = group.rows;
    
    addStatusMessage(`Processing group for image ID: ${imageId}`, 'info');
    
    // Create result object
    const imageResult = {
        filename: `${imageId}.txt`,
        description: "",  // Will be filled by vision model
        OCR_EN: ""  // Will be filled by text extraction
    };
    
    // Find the image file for this ID
    const matchingImage = findImageByID(imageId);
    
    if (matchingImage) {
        addStatusMessage(`Found matching image for ID: ${imageId}`, 'success');
        
        // First get image description using vision model
        getImageDescription(matchingImage, apiKey)
            .then(description => {
                imageResult.description = description;
                addStatusMessage(`Got image description: ${description.substring(0, 50)}...`, 'success');
                
                // Process each text item using the selected language model
                addStatusMessage(`Using ${model} for localization`, 'info');
                const textProcessingPromises = rows.map(row => {
                    return processLocalization(row.EN, apiKey, model, languages, customPrompt, description)
                        .then(localization => {
                            // Add localization to the result
                            const resultEntry = { "EN": row.EN };
                            
                            // Add all requested languages to the result
                            languages.forEach(langCode => {
                                const langName = getLanguageName(langCode).toLowerCase();
                                if (langName && localization[langName]) {
                                    // Apply character name replacements
                                    let translatedText = localization[langName];
                                    translatedText = replaceCharacterNames(translatedText, langName);
                                    resultEntry[langName] = translatedText;
                                } else if (langName) {
                                    resultEntry[langName] = `[No translation available for ${langName}]`;
                                }
                            });
                            
                            // Add to image result with LOCID key
                            imageResult[row.LOCID] = resultEntry;
                            
                            return resultEntry;
                        })
                        .catch(error => {
                            addStatusMessage(`Error processing text: ${error.message}`, 'error');
                            return null;
                        });
                });
                
                // Wait for all text items to be processed
                return Promise.all(textProcessingPromises);
            })
            .then(() => {
                // Add the complete image result to results array
                results.push(imageResult);
                
                // Update progress
                processedCount++;
                updateProgress(processedCount, totalGroups);
                
                // Small delay to avoid rate limits
                setTimeout(() => {
                    processNextGroup(apiKey, model, languages, customPrompt, results, totalGroups);
                }, 1500); // Longer delay to avoid rate limits with vision API
            })
            .catch(error => {
                addStatusMessage(`Error processing image: ${error.message}`, 'error');
                
                // Continue with next group
                processNextGroup(apiKey, model, languages, customPrompt, results, totalGroups);
            });
    } else {
        // No matching image, process without image description
        addStatusMessage(`No image found for ID: ${imageId}, proceeding with text-only localization`, 'warning');
        
        // Process each text item using the language model without image context
        const textProcessingPromises = rows.map(row => {
            return processLocalization(row.EN, apiKey, model, languages, customPrompt)
                .then(localization => {
                    // Add localization to the result
                    const resultEntry = { "EN": row.EN };
                    
                    // Add all requested languages to the result
                    languages.forEach(langCode => {
                        const langName = getLanguageName(langCode).toLowerCase();
                        if (langName && localization[langName]) {
                            // Apply character name replacements
                            let translatedText = localization[langName];
                            translatedText = replaceCharacterNames(translatedText, langName);
                            resultEntry[langName] = translatedText;
                        } else if (langName) {
                            resultEntry[langName] = `[No translation available for ${langName}]`;
                        }
                    });
                    
                    // Add to image result with LOCID key
                    imageResult[row.LOCID] = resultEntry;
                    
                    return resultEntry;
                })
                .catch(error => {
                    addStatusMessage(`Error processing text: ${error.message}`, 'error');
                    return null;
                });
        });
        
        // Wait for all text items to be processed
        Promise.all(textProcessingPromises)
            .then(() => {
                // Add the complete image result to results array
                results.push(imageResult);
                
                // Update progress
                processedCount++;
                updateProgress(processedCount, totalGroups);
                
                // Small delay to avoid rate limits
                setTimeout(() => {
                    processNextGroup(apiKey, model, languages, customPrompt, results, totalGroups);
                }, 1000);
            })
            .catch(error => {
                addStatusMessage(`Error: ${error.message}`, 'error');
                processNextGroup(apiKey, model, languages, customPrompt, results, totalGroups);
            });
    }
}

function updateProgress(current, total) {
    const percentage = Math.round((current / total) * 100);
    const progressBar = document.querySelector('#progressBar .progress-bar');
    progressBar.style.width = `${percentage}%`;
    progressBar.setAttribute('aria-valuenow', percentage);
    progressBar.textContent = `${percentage}%`;
}

function finishProcessing(results) {
    addStatusMessage('Processing complete!', 'success');
    
    // Update UI
    document.getElementById('startProcessing').disabled = false;
    document.getElementById('progressBar').classList.add('d-none');
    document.getElementById('results').classList.remove('d-none');
    
    // Store results for download
    window.localizationResults = results;
    
    // Create language-specific versions of the results (Format 2)
    window.languageResults = generateLanguageSpecificResults(results);
    
    // Create format selection UI
    createFormatSelectionUI();
    
    // Show preview of the default format
    const jsonOutput = document.getElementById('jsonOutput');
    jsonOutput.textContent = JSON.stringify(results, null, 2);
}

// Generate language-specific JSON format (Format 2)
function generateLanguageSpecificResults(results) {
    const languageData = {};
    
    // First, identify all languages used
    const languages = new Set();
    results.forEach(item => {
        Object.keys(item).forEach(key => {
            if (typeof item[key] === 'object' && item[key] !== null) {
                Object.keys(item[key]).forEach(lang => {
                    if (lang !== 'EN') {
                        languages.add(lang);
                    }
                });
            }
        });
    });
    
    // Always include English
    languages.add('EN');
    languageData['EN'] = {};
    
    // Initialize language objects
    languages.forEach(lang => {
        languageData[lang] = {};
    });
    
    // Mapping for key name changes
    const keyMappings = {
        'LEVEL_TEXT': 'question',
        'HINT': 'hint',
        'END': 'endText'
    };
    
    // Process character names using chars.json before localization
    const processCharacterNames = (text) => {
        if (!window.characterData || Object.keys(window.characterData).length === 0) {
            return text; // No character data available
        }
        
        let processedText = text;
        
        // Apply character name replacements
        Object.keys(window.characterData).forEach(charName => {
            const charData = window.characterData[charName];
            if (charData && charData.variations) {
                // Create regex with word boundaries to replace full character names
                const regex = new RegExp(`\\b${escapeRegExp(charName)}\\b`, 'g');
                processedText = processedText.replace(regex, charName);
                
                // Also replace any known variations
                if (Array.isArray(charData.variations)) {
                    charData.variations.forEach(variation => {
                        if (variation && variation !== charName) {
                            const variationRegex = new RegExp(`\\b${escapeRegExp(variation)}\\b`, 'g');
                            processedText = processedText.replace(variationRegex, charName);
                        }
                    });
                }
            }
        });
        
        return processedText;
    };
    
    // Function to clean text content
    const cleanTextContent = (text) => {
        if (!text) return '';
        
        // Remove explanations and translations
        let cleanedText = text;
        
        // First, remove specific explanation patterns
        const explanationPatterns = [
            /Explanation:.*/g,
            /Note:.*/g,
            /\(Note:.*/g, 
            /- This.*/g,
            /- ".*" is.*/g,
            /\*\(Note:.*/g,
            /\*\*German:\*\*.*/g,
            /German:.*/g,
            /> Explanation:.*/g,
            /\(Literal:.*/g
        ];
        
        for (const pattern of explanationPatterns) {
            cleanedText = cleanedText.replace(pattern, '');
        }
        
        // Remove content after common explanation indicators
        const cutoffPoints = [
            '**German:**',
            '### German:',
            '- Explanation:',
            'Explanation:',
            '### Notes:',
            '✅ Notes:',
            '*(Note:',
            '---',
            '✅',
            ' - ',
            ' > ',
            ' - "'
        ];
        
        for (const cutPoint of cutoffPoints) {
            const index = cleanedText.indexOf(cutPoint);
            if (index !== -1) {
                cleanedText = cleanedText.substring(0, index);
            }
        }
        
        // Remove special characters
        cleanedText = cleanedText.replace(/\*/g, ''); // Asterisks
        cleanedText = cleanedText.replace(/\n/g, ' '); // Newlines
        cleanedText = cleanedText.replace(/\-/g, ''); // Hyphens at end
        
        // Clean up formatting issues
        cleanedText = cleanedText.replace(/^\s*"(.*)"\s*$/, '$1'); // Remove surrounding quotes
        cleanedText = cleanedText.replace(/^["']|["']$/g, ''); // Remove quotes at beginning/end
        
        // Remove multiple spaces and trim
        cleanedText = cleanedText.replace(/\s+/g, ' ').trim();
        
        return cleanedText;
    };
    
    // Collect strings for each language
    results.forEach((item, itemIndex) => {
        // Get sequence number (1-based) for the item
        const sequenceNumber = itemIndex + 1;
        
        Object.keys(item).forEach(key => {
            // Skip non-translatable fields
            if (key === 'filename' || key === 'description' || key === 'OCR_EN') {
                return;
            }
            
            // Process translatable entries
            if (typeof item[key] === 'object' && item[key] !== null) {
                // Extract base key type and sequence
                let baseKeyMatch = key.match(/([A-Z_]+)(?:_?(\d+))?(?:_?(\d+))?/);
                
                if (baseKeyMatch) {
                    const baseKey = baseKeyMatch[1]; // LEVEL_TEXT, HINT, END, etc.
                    let sequence1 = baseKeyMatch[2] || sequenceNumber.toString();
                    let sequence2 = baseKeyMatch[3] || '1'; // Default to 1 if no second sequence
                    
                    // Map the key type to new format if needed
                    let newKeyType = keyMappings[baseKey] || baseKey.toLowerCase();
                    
                    // Format the new key name (no double underscore)
                    let newKey;
                    if (baseKey === 'LEVEL_TEXT' || baseKey === 'END') {
                        newKey = `${newKeyType}_${sequence1}`;
                    } else {
                        newKey = `${newKeyType}_${sequence1}_${sequence2}`;
                    }
                    
                    // Add translated content for each language
                    languages.forEach(lang => {
                        if (item[key][lang]) {
                            // Process text: first clean it, then apply character name standardization
                            let processedText = cleanTextContent(item[key][lang]);
                            processedText = processCharacterNames(processedText);
                            
                            // Store the fully processed text
                            languageData[lang][newKey] = processedText;
                        } else if (item[key]['EN'] && lang !== 'EN') {
                            // If translation is missing but English exists, use English
                            languageData[lang][newKey] = '[MISSING TRANSLATION] ' + cleanTextContent(item[key]['EN']);
                        }
                    });
                } else {
                    // Fallback for keys that don't match the pattern
                    languages.forEach(lang => {
                        if (item[key][lang]) {
                            languageData[lang][key.toLowerCase()] = cleanTextContent(item[key][lang]);
                        }
                    });
                }
            }
        });
    });
    
    return languageData;
}

// Create UI for format selection
function createFormatSelectionUI() {
    const formatSelector = document.createElement('div');
    formatSelector.className = 'mb-3';
    formatSelector.innerHTML = `
        <label class="form-label">JSON Format:</label>
        <div class="form-check">
            <input class="form-check-input" type="radio" name="jsonFormat" id="formatFull" value="full" checked>
            <label class="form-check-label" for="formatFull">Full Format - All languages in one file</label>
        </div>
        <div class="form-check">
            <input class="form-check-input" type="radio" name="jsonFormat" id="formatLang" value="language">
            <label class="form-check-label" for="formatLang">Language-specific files (strings_en, strings_tr, etc.)</label>
        </div>
    `;
    
    // Add format selector before the download button
    const resultsDiv = document.getElementById('results');
    const downloadButton = document.getElementById('downloadJson');
    resultsDiv.insertBefore(formatSelector, downloadButton);
    
    // Add event listeners for format change
    document.querySelectorAll('input[name="jsonFormat"]').forEach(radio => {
        radio.addEventListener('change', updateJsonPreview);
    });
}

// Update the JSON preview based on selected format
function updateJsonPreview() {
    const formatType = document.querySelector('input[name="jsonFormat"]:checked').value;
    const jsonOutput = document.getElementById('jsonOutput');
    
    if (formatType === 'full') {
        // Show full format
        jsonOutput.textContent = JSON.stringify(window.localizationResults, null, 2);
    } else {
        // Show language-specific format (preview the first language)
        const languages = Object.keys(window.languageResults);
        if (languages.length > 0) {
            const previewLang = languages[0];
            jsonOutput.textContent = `// Preview of ${previewLang} strings\n` + 
                JSON.stringify(window.languageResults[previewLang], null, 2) + 
                `\n\n// Note: Downloads will include separate files for each language.`;
        }
    }
}

function downloadJson() {
    if (!window.localizationResults) {
        addStatusMessage('No results to download.', 'error');
        return;
    }
    
    // Generate timestamp
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    
    // Check which format is selected
    const formatType = document.querySelector('input[name="jsonFormat"]:checked').value;
    
    if (formatType === 'full') {
        // Download the full format (Format 1)
        const dataStr = JSON.stringify(window.localizationResults, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        
        const a = document.createElement('a');
        a.href = URL.createObjectURL(dataBlob);
        a.download = `localization_${timestamp}.json`;
        a.click();
        
        addStatusMessage('Downloaded JSON file.', 'success');
    } else {
        // Download language-specific files (Format 2)
        const languages = Object.keys(window.languageResults);
        
        // Create a zip file with all language-specific JSONs
        if (window.JSZip) {
            const zip = new JSZip();
            
            // Add each language file to the zip
            languages.forEach(lang => {
                const langData = JSON.stringify(window.languageResults[lang], null, 2);
                // Use lowercase for file naming convention
                const fileName = `strings_${lang.toLowerCase()}.json`;
                zip.file(fileName, langData);
            });
            
            // Generate and download the zip
            zip.generateAsync({ type: 'blob' }).then(content => {
                const a = document.createElement('a');
                a.href = URL.createObjectURL(content);
                a.download = `localization_languages_${timestamp}.zip`;
                a.click();
                
                addStatusMessage(`Downloaded ${languages.length} language files as ZIP.`, 'success');
            });
        } else {
            // Fallback if JSZip is not available
            languages.forEach(lang => {
                const langData = JSON.stringify(window.languageResults[lang], null, 2);
                const dataBlob = new Blob([langData], { type: 'application/json' });
                
                const a = document.createElement('a');
                a.href = URL.createObjectURL(dataBlob);
                a.download = `strings_${lang.toLowerCase()}_${timestamp}.json`;
                a.click();
            });
            
            addStatusMessage(`Downloaded ${languages.length} language files.`, 'success');
        }
    }
}

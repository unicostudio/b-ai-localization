// Game Localization Tool - API Functions

// Default vision model - this value is used when calling the OpenRouter API
const VISION_MODEL_ID = 'openai/chatgpt-4o-latest';

// Available model mappings (matching Python version)
// Using window.MODEL_IDS to make it globally accessible across all JS files
window.MODEL_IDS = {
    "grok3": "x-ai/grok-3-beta",
    "gpt-4o": "openai/gpt-4.1",
    "claude-3-7-sonnet": "anthropic/claude-3.7-sonnet",
    "gemini-1.5-pro": "google/gemini-flash-1.5-8b"
};


// Find image by ID
function findImageByID(imageId) {
    // Convert ID to a string and remove "ID" prefix if present
    const idNum = imageId.toString().replace(/^ID/i, '');
    
    // Look for images with the ID in their filename
    for (const image of uploadedImages) {
        if (image.name.includes(idNum)) {
            return image;
        }
    }
    
    addStatusMessage(`Warning: No image found for ID ${imageId}`, 'warning');
    return null;
}

// Get image description using Vision API
function getImageDescription(imageFile, apiKey) {
    return new Promise((resolve, reject) => {
        if (!imageFile) {
            resolve("No image available");
            return;
        }
        
        addStatusMessage(`Getting image description for ${imageFile.name}...`, 'info');
        
        // Read the image as base64
        const reader = new FileReader();
        reader.onload = function(e) {
            const base64Image = e.target.result.split(',')[1]; // Remove the data URL prefix
            
            // Call the vision model API
            fetch('https://openrouter.ai/api/v1/chat/completions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${apiKey}`,
                    'HTTP-Referer': 'https://unicostudio.github.io/b-ai-localization/',
                    'X-Title': 'Game Localization Tool'
                },
                body: JSON.stringify({
                    model: VISION_MODEL_ID,
                    messages: [
                        {
                            role: 'user',
                            content: [
                                { type: 'text', text: 'Please describe what you see in this game image. Focus on the key elements, characters, and actions visible. Keep it brief (less than 5 sentences).' },
                                { type: 'image_url', image_url: { url: `data:image/jpeg;base64,${base64Image}` } }
                            ]
                        }
                    ],
                    max_tokens: 300,
                    temperature: 0.2
                })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Vision API error: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                // Extract the description from the response
                if (data.choices && data.choices.length > 0 && data.choices[0].message) {
                    const description = data.choices[0].message.content;
                    resolve(description);
                } else {
                    throw new Error('Invalid response from vision API');
                }
            })
            .catch(error => {
                addStatusMessage(`Error getting image description: ${error.message}`, 'error');
                resolve("Error getting image description"); // Still resolve to continue processing
            });
        };
        
        reader.onerror = function() {
            addStatusMessage('Error reading image file', 'error');
            resolve("Error reading image file");
        };
        
        reader.readAsDataURL(imageFile);
    });
}

// Process localization using language model
function processLocalization(englishText, apiKey, model, languages, customPrompt, imageDescription = "") {
    return new Promise((resolve, reject) => {
        // For testing, you can set this to true to use mock data instead of real API calls
        const debugMode = false;
        
        if (debugMode) {
            // Create mock translations for testing
            const result = { english: englishText };
            
            languages.forEach(langCode => {
                const langName = getLanguageName(langCode).toLowerCase();
                if (langName) {
                    result[langName] = `[${langCode}] ${englishText}`;
                }
            });
            
            // Simulate API delay
            setTimeout(() => {
                resolve(result);
            }, 500);
            
            return;
        }
        
        // Get model ID
        const modelIds = {
            'gpt4o': 'openai/chatgpt-4o-latest',
            'claude3opus': 'anthropic/claude-3-opus',
            'claude3sonnet': 'anthropic/claude-3-sonnet',
            'claude3haiku': 'anthropic/claude-3-haiku',
            'gpt4': 'openai/gpt-4-turbo-preview',
            'grok3': 'x-ai/grok-3-beta',
            'llama3': 'meta/llama-3-70b-instruct'
        };
        
        const modelId = modelIds[model] || 'openai/chatgpt-4o-latest';
        
        // Create a comma-separated list of the language names
        const languageNames = languages.map(langCode => getLanguageName(langCode).title()).join(', ');
        
        // Add image description to prompt if available
        const contextPrompt = imageDescription ? `\n\nImage Context: ${imageDescription}\n` : '';
        
        // Build the messages for the API
        const systemPrompt = customPrompt || gamePrompts['brain-test-1'];
        const userPrompt = `
English Text: ${englishText}${contextPrompt}

Please provide localized versions in ${languageNames} that preserve the meaning, humor, and game mechanic while being culturally appropriate.
`;
        
        // Make OpenRouter API request
        fetch('https://openrouter.ai/api/v1/chat/completions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${apiKey}`,
                'HTTP-Referer': 'https://unicostudio.github.io/b-ai-localization/',
                'X-Title': 'Game Localization Tool'
            },
            body: JSON.stringify({
                model: modelId,
                messages: [
                    { role: 'system', content: systemPrompt },
                    { role: 'user', content: userPrompt }
                ],
                max_tokens: 512,
                temperature: 0.3
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Extract response
            const responseText = data.choices[0].message.content;
            
            // Parse the response to extract localizations
            const localization = { english: englishText };
            
            addStatusMessage(`Received localization response for: ${englishText.substring(0, 30)}...`, 'success');
            
            // Extract translations for each language
            languages.forEach(langCode => {
                const langName = getLanguageName(langCode).toLowerCase();
                if (!langName) return;
                
                // Create pattern for this language
                const pattern = new RegExp(`(?:${langName.title()}|${langName.toUpperCase()})\\s*:(.+?)(?=(\\n\\n[A-Z]|$))`, 'is');
                const match = responseText.match(pattern);
                
                if (match && match[1]) {
                    // Clean the text
                    let text = match[1].trim();
                    
                    // Remove "Text:" prefix if present
                    if (text.includes("**Text:**")) {
                        text = text.replace(/\*\*Text:\*\*\s*/, '');
                    }
                    
                    // Remove any explanation sections
                    const explanationMatch = text.match(/(\*\*Explanation:|\n\n\*\*Explanation:)/);
                    if (explanationMatch) {
                        text = text.substring(0, explanationMatch.index).trim();
                    }
                    
                    // Store the cleaned translation
                    localization[langName] = text;
                } else {
                    localization[langName] = `Could not extract ${langName} localization`;
                }
            });
            
            resolve(localization);
        })
        .catch(error => {
            addStatusMessage(`API error: ${error.message}`, 'error');
            reject(new Error(`API error: ${error.message}`));
        });
    });
}

// Global character data variable 
window.characterData = {};
window.customCharacterData = null;

// Initialize character data from HTML or load default from file
function initializeCharacterData() {
    try {
        // First try to get character data from HTML
        const charDataElem = document.getElementById('characterData');
        if (charDataElem) {
            window.characterData = JSON.parse(charDataElem.textContent);
            console.log('Character data loaded successfully from HTML');
            return true;
        }
        
        // If no character data in HTML, try to load default file
        return loadDefaultCharacterData();
    } catch (error) {
        console.error('Error loading character data from HTML:', error);
        return loadDefaultCharacterData();
    }
}

// Load default character data from JSON file
function loadDefaultCharacterData() {
    return fetch('data/default-characters.json')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to load default character data');
            }
            return response.json();
        })
        .then(data => {
            // Format data into the expected structure
            const formattedData = formatCharacterData(data);
            window.characterData = formattedData;
            console.log('Default character data loaded successfully');
            addStatusMessage('Loaded default character mappings', 'info');
            return true;
        })
        .catch(error => {
            console.error('Error loading default character data:', error);
            addStatusMessage('Failed to load default character mappings', 'warning');
            window.characterData = createEmptyCharacterData();
            return false;
        });
}

// Format character data from the default JSON format to the expected structure
function formatCharacterData(characterArray) {
    const formatted = {};
    
    // Process each character
    characterArray.forEach(character => {
        const englishName = character['Character Name (EN)'];
        if (!englishName) return;
        
        // Go through each language
        Object.keys(character).forEach(key => {
            if (key === 'Character Name (EN)' || key === 'EN') return;
            
            // Format language code
            let langCode = key.toLowerCase();
            // Handle special cases
            if (langCode === 'cn_tr') langCode = 'chinese';
            if (langCode === 'jp') langCode = 'japanese';
            if (langCode === 'kr') langCode = 'korean';
            if (langCode === 'ar') langCode = 'arabic';
            if (langCode === 'cz (cestina)') langCode = 'czech';
            if (langCode === 'hu (magyar)') langCode = 'hungarian';
            if (langCode === 'pl (polski)') langCode = 'polish';
            if (langCode === 'th (thai)') langCode = 'thai';
            if (langCode === 'vn (vietnam)') langCode = 'vietnamese';
            
            // Initialize language object if needed
            if (!formatted[langCode]) {
                formatted[langCode] = {};
            }
            
            // Add character mapping if value exists
            if (character[key]) {
                formatted[langCode][englishName] = character[key];
            }
        });
    });
    
    return formatted;
}

// Create empty character data structure
function createEmptyCharacterData() {
    return {
        'turkish': {'Lily': 'Bilmiş Bediş'},
        'french': {'Lily': 'Lily Facétie'},
        'german': {'Lily': 'Listige Lilli'}
    };
}

// Replace character names based on loaded character data
function replaceCharacterNames(text, language) {
    // Skip if text is empty
    if (!text) {
        return text;
    }
    
    // Make sure character data is initialized
    if (Object.keys(window.characterData).length === 0) {
        initializeCharacterData();
    }
    
    // Use custom character data if available, otherwise fall back to default
    const dataToUse = window.customCharacterData || window.characterData;
    
    // Skip if no character data exists for this language
    if (!dataToUse || !dataToUse[language]) {
        return text;
    }
    
    // Get character replacements for this language
    const charData = dataToUse[language];
    
    // Start with the original text
    let result = text;
    
    // Build a map of all variations to their localized names
    const variationMap = {};
    
    // Process each character name in the localization data
    Object.keys(charData).forEach(englishName => {
        const localizedName = charData[englishName];
        const englishLower = englishName.toLowerCase();
        
        // Add the original name mapping
        variationMap[englishLower] = localizedName;
        
        // Handle multi-word names (e.g., "Lazy Larry")
        const parts = englishName.split(' ');
        
        if (parts.length > 1) {
            // Add last name as a variation (e.g., "Larry" for "Lazy Larry")
            // Only if it's reasonably long to avoid matching common words
            const lastName = parts[parts.length - 1];
            if (lastName.length > 3) {
                variationMap[lastName.toLowerCase()] = localizedName;
            }
            
            // Handle prefixed names (like "Doctor Worry" → "Dr Worry" or just "Doctor")
            const prefixWord = parts[0].toLowerCase();
            const importantPrefixes = ['doctor', 'dr', 'uncle', 'aunt', 'granny', 'grandmother', 'lazy', 'little', 'the'];
            
            if (importantPrefixes.includes(prefixWord)) {
                // Add rest of name without prefix (e.g., "Worry" for "Doctor Worry")
                const nameWithoutPrefix = parts.slice(1).join(' ');
                if (nameWithoutPrefix.length > 3) {
                    variationMap[nameWithoutPrefix.toLowerCase()] = localizedName;
                }
                
                // Add just the title/prefix for distinctive prefixes
                if (['doctor', 'dr', 'granny', 'uncle'].includes(prefixWord)) {
                    variationMap[prefixWord] = localizedName;
                }
                
                // If the prefix is "The", add the rest as a variation
                if (prefixWord === 'the') {
                    variationMap[parts.slice(1).join(' ').toLowerCase()] = localizedName;
                }
            }
        }
    });
    
    // Add manual variation mappings for common misspellings and shortened forms
    const variations = {
        // Character: [variations]
        "lily": ["lilly", "lillie", "lil"],
        "larry": ["lary", "larrry", "larrie"],
        "doctor worry": ["dr worry", "doc worry", "doctor", "dr", "worry"],
        "granny amy": ["granny", "grandma amy", "grandmother amy", "amy"],
        "uncle bubba": ["bubba", "uncle"],
        "bubba": ["buba", "bubber", "bubbah"],
        "astrodog": ["astro dog", "astro", "space dog"],
        "martian": ["the martian"],
        "rockhead": ["the rockhead", "rock head", "rock"],
        "jenny": ["jen", "jenn", "jennie"],
        "judy": ["judi", "judie"],
        "gymmy": ["jimmy", "jimy", "gym"],
        "little tiki": ["tiki", "little"],
        "lazy larry": ["lazy", "larry"]
    };
    
    // Add all the variations to our mapping
    Object.keys(variations).forEach(base => {
        const baseLower = base.toLowerCase();
        // If we have a localized version for this base name
        if (variationMap[baseLower]) {
            const localizedVersion = variationMap[baseLower];
            // Add all variations
            variations[base].forEach(variation => {
                variationMap[variation.toLowerCase()] = localizedVersion;
            });
        }
    });
    
    // Sort the keys by length (longest first) to ensure we replace the most specific matches first
    const sortedKeys = Object.keys(variationMap).sort((a, b) => b.length - a.length);
    
    // Apply all the replacements
    for (const englishVariation of sortedKeys) {
        const localizedName = variationMap[englishVariation];
        // Use word boundaries to avoid replacing parts of words
        const pattern = new RegExp('\\b' + escapeRegExp(englishVariation) + '\\b', 'gi');
        result = result.replace(pattern, localizedName);
    }
    
    return result;
}

function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function getLanguageName(code) {
    const langMap = {
        'TR': 'turkish',
        'FR': 'french',
        'DE': 'german',
        'ES': 'spanish',
        'IT': 'italian',
        'PT': 'portuguese',
        'RU': 'russian',
        'JP': 'japanese',
        'KR': 'korean',
        'CN_TR': 'chinese',
        'TH': 'thai',
        'VN': 'vietnamese',
        'ID': 'indonesian',
        'MY': 'malay',
        'RO': 'romanian',
        'AR': 'arabic',
        'PL': 'polish',
        'CZ': 'czech',
        'HU': 'hungarian'
    };
    
    return langMap[code] || code.toLowerCase();
}

// Helper extension method
String.prototype.title = function() {
    return this.charAt(0).toUpperCase() + this.slice(1);
};

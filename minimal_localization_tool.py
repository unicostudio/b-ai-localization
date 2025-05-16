#!/usr/bin/env python3
import os
import json
import argparse
import base64
import time
import csv
import re
import requests
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

# Get API key from environment variable
DEFAULT_OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not DEFAULT_OPENROUTER_API_KEY:
    print("Warning: OPENROUTER_API_KEY environment variable not set. You will need to provide an API key through the web interface.")

# Initialize OpenAI client with OpenRouter base URL
# We'll create the client with a specific API key when needed
def create_openai_client(api_key=None):
    """Create an OpenAI client with the specified API key or default"""
    # Use provided API key or fall back to environment variable
    key_to_use = api_key if api_key else DEFAULT_OPENROUTER_API_KEY
    
    # Return client with the appropriate key
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=key_to_use,
    )

# Define the model to use for localization
#MODEL_ID = "x-ai/grok-3-beta"

# OpenRouter model IDs
#VISION_MODEL_ID = "openai/gpt-4-vision-preview"
VISION_MODEL_ID = "openai/chatgpt-4o-latest"
# Available model mappings
MODEL_IDS = {
    "grok3": "x-ai/grok-3-beta",
    "gpt-4o": "openai/gpt-4.1",
    "claude-3-7-sonnet": "anthropic/claude-3.7-sonnet",
    "gemini-1.5-pro": "google/gemini-flash-1.5-8b"
}

# Define language codes for output
LANGUAGE_CODES = {
    "turkish": "tr",
    "french": "fr",
    "german": "de",
    "spanish": "es",
    "italian": "it",
    "portuguese": "pt",
    "russian": "ru",
    "japanese": "jp",
    "korean": "kr",
    "thai": "th",
    "vietnamese": "vn",
    "indonesian": "id",
    "malay": "my",
    "romanian": "ro",
    "arabic": "ar",
    "polish": "pl",
    "czech": "cz",
    "hungarian": "hu",
    "chinese": "cn_tr"
}

# Map language codes to language names
LANGUAGE_NAMES = {
    "TR": "turkish",
    "FR": "french",
    "DE": "german",
    "ES": "spanish",
    "IT": "italian",
    "PT": "portuguese",
    "RU": "russian",
    "JP": "japanese",
    "KR": "korean",
    "TH": "thai",
    "VN": "vietnamese",
    "ID": "indonesian",
    "MY": "malay",
    "RO": "romanian",
    "AR": "arabic",
    "PL": "polish",
    "CZ": "czech",
    "HU": "hungarian",
    "CN_TR": "chinese"
}

def encode_image(image_path):
    """Encode image to base64 for API request"""
    try:
        with open(image_path, "rb") as image_file:
            # Simple base64 encoding without the data URL prefix
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Error encoding image: {str(e)}")
        return None

def find_image_by_id(images_dir, image_id):
    """Find an image file by its ID in the filename"""
    # Convert image_id to string and remove "ID" prefix if present
    id_num = image_id.replace("ID", "") if image_id.startswith("ID") else image_id
    
    # Look for files with names containing the ID
    pattern = re.compile(r".*ID" + id_num + r"\..*$", re.IGNORECASE)
    
    for filename in os.listdir(images_dir):
        if pattern.match(filename):
            return os.path.join(images_dir, filename)
    
    return None

def manual_ocr(image_path):
    """
    Placeholder for OCR - in production, you would need to implement 
    an alternative OCR method or use a service API
    """
    print(f"⚠️ OCR not implemented for image: {os.path.basename(image_path)}")
    return f"[OCR text for {os.path.basename(image_path)} would appear here]"

def get_image_description(image_path, api_key=None, debug=False):
    """Get description of image using GPT 4o Vision model (limited to 5 sentences)"""
    print(f"\n🔍 Getting image description for {os.path.basename(image_path)}...")
    
    if debug:
        print("  DEBUG MODE: Returning mock description instead of calling API")
        return f"This is a debug description for image {os.path.basename(image_path)}. It contains no more than 5 sentences. The image shows a game screen. There's a character and some objects. The player needs to solve a puzzle."
    
    # Use provided API key or default
    api_key_to_use = api_key if api_key else DEFAULT_OPENROUTER_API_KEY
    if not api_key_to_use:
        print("✗ No API key available for image description")
        return "Error: No API key available for image description"
    
    # Convert the image to base64
    base64_image = encode_image(image_path)
    if not base64_image:
        return "Error: Failed to encode image"
    
    try:
        # Direct API request to OpenRouter with timeout and retry logic
        max_retries = 2
        retry_count = 0
        timeout_seconds = 20
        
        while retry_count <= max_retries:
            try:
                print(f"Attempt {retry_count + 1} to connect to vision API...")
                response = requests.post(
                    url="https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key_to_use}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://cascade.ai",  # Site URL for rankings
                        "X-Title": "Game Localization Tool",  # Site title for rankings
                    },
                    json={
                        "model": VISION_MODEL_ID,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a detailed image description expert for a mobile game. Examine the game screenshot and create a concise description that includes the main elements, puzzle/challenge, visible text, and overall theme. Keep your description to a maximum of 5 sentences."
                            },
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": "What does this game screenshot show?"
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{base64_image}"
                                        }
                                    }
                                ]
                            }
                        ],
                        "max_tokens": 300
                    },
                    timeout=timeout_seconds
                )
                # If we got here, the request succeeded, so break the retry loop
                break
            except requests.exceptions.Timeout:
                retry_count += 1
                print(f"Request timed out after {timeout_seconds} seconds. Retry {retry_count}/{max_retries}")
                if retry_count > max_retries:
                    raise Exception(f"API request timed out after {max_retries} retries")
                time.sleep(2)  # Wait before retrying
            except requests.exceptions.RequestException as req_err:
                print(f"Request error: {str(req_err)}")
                # For connection errors, we'll retry
                if "ConnectionError" in str(req_err) or "ConnectTimeout" in str(req_err):
                    retry_count += 1
                    if retry_count > max_retries:
                        raise
                    time.sleep(2)  # Wait before retrying
                else:
                    # For other request errors, raise immediately
                    raise
        
        # Parse the response
        result = response.json()
        
        # Debug information
        print(f"\n📋 Vision API Response Structure: {list(result.keys())}")
        print(f"Response keys: {', '.join(result.keys())}")


        # Handle potential response structures
        if 'choices' in result and len(result['choices']) > 0:
            # Standard OpenAI/OpenRouter format
            if 'message' in result['choices'][0]:
                description = result['choices'][0]['message']['content']
                print("Standard format response detected")

            # Alternative format sometimes returned
            elif 'text' in result['choices'][0]:
                description = result['choices'][0]['text']
                print("Alternative format response detected")
            else:
                # Debug the exact structure
                print(f"\n🔍 Choices structure: {result['choices'][0]}")
                try:
                    print(f"Choices keys: {', '.join(result['choices'][0].keys())}")
                except:
                    print("Could not get choice keys")

                print("❌ Could not locate content in response")

                return "Error: Could not extract content from vision API response"
            
            # Ensure description is not more than 5 sentences
            sentences = re.split(r'(?<=[.!?])\s+', description)

            if len(sentences) > 5:
                description = ' '.join(sentences[:5])
            
            print(f"✓ Successfully obtained image description: {description[:50]}...")

            return description
        # Special handling for some API response formats
        elif 'error' in result:
            print(f"❌ API returned error: {result['error']}")
            try:
                if isinstance(result['error'], dict) and 'message' in result['error']:
                    print(f"Error message: {result['error']['message']}")
            except:
                print("Could not extract detailed error message")
                
            # Instead of returning an error, provide a generic description to allow processing to continue
            print("⚠️ Using fallback description due to API error")
            image_name = os.path.basename(image_path)
            return f"This appears to be a game screen from mobile game. There may be a character and some interactive elements. The player likely needs to solve a puzzle by interacting with objects on the screen. File: {image_name}"
        else:
            print(f"❌ Unexpected response format with keys: {list(result.keys())}")
            print("Attempting to find usable content in response")

            # Attempt to extract content from any key that might contain it
            for key in ['response', 'output', 'generated_text', 'completion']:
                if key in result:
                    print(f"Found possible content in '{key}' field")

                    return result[key]
            
            return "Error: Invalid response format from vision API"
    
    except Exception as e:
        print(f"✗ Error getting image description: {str(e)}")
        # Instead of returning an error, provide a generic description to allow processing to continue
        print("⚠️ Using fallback description due to exception")
        image_name = os.path.basename(image_path)
        return f"This is likely a game screen showing interactive elements. The player appears to be presented with a puzzle or challenge to solve. There may be instructions or game elements visible on screen. File: {image_name}"

def load_character_data(chars_file):
    """Load character data from JSON file"""
    try:
        if not os.path.exists(chars_file):
            print(f"⚠️ Character file not found: {chars_file}")
            return {}
            
        with open(chars_file, 'r', encoding='utf-8') as f:
            chars_data = json.load(f)
            
        # Create a lookup dictionary for each language
        char_lookup = {
            "turkish": {},
            "french": {},
            "german": {}
        }
        
        # Process each character
        for char in chars_data:
            en_name = char.get("Character Name (EN)", "") or char.get("EN", "")
            if en_name:
                if "TR" in char and char["TR"]:
                    char_lookup["turkish"][en_name] = char["TR"]
                if "FR" in char and char["FR"]:
                    char_lookup["french"][en_name] = char["FR"]
                if "DE" in char and char["DE"]:
                    char_lookup["german"][en_name] = char["DE"]
        
        print(f"✓ Successfully loaded character data for {len(chars_data)} characters")
        return char_lookup
    except Exception as e:
        print(f"✗ Error loading character data: {str(e)}")
        return {}

def replace_character_names(text, language, char_lookup):
    """Replace character names in the given text with localized versions"""
    # Skip if no character data exists for this language
    if language not in char_lookup:
        return text
    
    # Get character replacements for this language
    char_data = char_lookup[language]
    
    # Get all character names in the text
    result = text
    
    # Apply character replacements
    for english_name, localized_name in char_data.items():
        # Create a pattern to match the English name, with proper case sensitivity
        # Handle both normal cases (Lily) and special cases (Lilly/Bediş)
        pattern = r'\b' + re.escape(english_name) + r'\b'
        result = re.sub(pattern, localized_name, result, flags=re.IGNORECASE)
        
        # Also handle common misspellings (like Lilly instead of Lily)
        if english_name.lower() == "lily" and "lilly" in result.lower():
            result = re.sub(r'\bLilly\b', localized_name, result, flags=re.IGNORECASE)
        
    return result

def process_localization(description, english_text, model="grok3", languages=None, debug=False, char_lookup=None, api_key=None, custom_prompt=None):
    """Process localization using the selected model"""
    # Default languages if none specified
    if languages is None:
        languages = ["TR", "FR", "DE"]
    
    # Get model ID
    model_id = MODEL_IDS.get(model, "x-ai/grok-3")
    print(f"\n🔄 Processing localization for text: {english_text[:50]}... using {model_id}")
    print(f"  Selected languages: {', '.join(languages)}")
    
    if debug:
        print("  DEBUG MODE: Returning mock translations instead of calling API")
        # Create result dictionary with mock translations for selected languages
        result = {"english": english_text}
        
        # Mock translations for all supported languages
        for lang_code in languages:
            lang_name = LANGUAGE_NAMES.get(lang_code.upper(), "").lower()
            if lang_name in LANGUAGE_CODES:
                lang_key = LANGUAGE_CODES[lang_name]
                mock_text = f"[{lang_code}] {english_text}"
                
                # Apply character name replacements if available
                if char_lookup and lang_name in char_lookup:
                    mock_text = replace_character_names(mock_text, lang_name, char_lookup)
                    
                result[lang_key] = mock_text
                
        return result
    
    # Use custom prompt if provided, otherwise use default
    if custom_prompt:
        # Replace placeholders in the custom prompt
        system_prompt = custom_prompt
    else:
        # Default context prompt explaining what we want
        system_prompt = f"""
    You are a game localization translator expert.

    You have been provided with an image description and English text from a 'Brain Test' puzzle game.
    You can use the following information for localization:
        
        You're localizing a 'Brain Test' named children's brain teaser game that uses word play, 
        Brain Test is a children's brain teaser game that is popular worldwide, known for its tricky and often unexpected brain teasers.
        
        IMPORTANT NOTE: DO NOT translate any character names in the text. Keep all character names as they are in English.
        Character names like Lily, Granny Amy, Uncle Bubba, etc. should remain unchanged in your translation.
        These will be replaced with the proper localized names in a separate step.
        
        more information about the game:
        
        https://play.google.com/store/apps/details?id=com.unicostudio.braintest&hl=tr
    
    Image Description:
    {description}
    
    Your task is to provide culturally-appropriate localizations of the English text in the following languages:
    {', '.join([LANGUAGE_NAMES.get(lang_code.upper(), 'Unknown').title() for lang_code in languages])}
    
    For localization, use cultural references, idioms, and wordplay specific to each language.
    
    These should preserve the game mechanics, humor, and puzzle elements but adapt them to feel natural 
    in each target language.

    Format your response for each language as follows:
    
    {"\n    ".join([f"{LANGUAGE_NAMES.get(lang_code.upper(), 'Unknown').title()}: [Translated text only]" for lang_code in languages])}
    
    Do not include ANY additional explanations, notes, or context in your response.
    Do not include the "Localization:**" prefix or any explanation section.
    Return ONLY the direct translations for each language.
    """
    
    try:
        # Build the message with English text
        # Create a comma-separated list of the language names
        language_list = ', '.join([LANGUAGE_NAMES.get(lang_code.upper(), 'Unknown').title() for lang_code in languages])
        
        user_prompt = f"""
English Text: {english_text}

Please provide localized versions in {language_list} that preserve the meaning, humor, and game mechanic while being culturally appropriate.
"""
        
        # Create client with the custom API key or default
        client = create_openai_client(api_key)
        
        # Call the selected model with OpenRouter headers
        response = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://cascade.ai",  # Site URL for rankings
                "X-Title": "Game Localization Tool",   # Site title for rankings
            },
            model=model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=512,
            temperature=0.3,
        )
        
        # Extract response
        response_text = response.choices[0].message.content
        
        # Parse the response to extract localizations
        localization = {
            "english": english_text
        }
        
        # Create dynamic patterns for matching each language translation
        patterns = {}
        
        # Get all language names from the selected codes
        selected_lang_names = [LANGUAGE_NAMES.get(lang_code.upper(), "").lower() for lang_code in languages]
        
        # Generate the regex patterns for each language
        for i, lang_name in enumerate(selected_lang_names):
            if not lang_name:
                continue
                
            # Get the next language name(s) to use as boundary or end-of-string
            next_langs = selected_lang_names[i+1:]
            boundary = ""
            
            if next_langs:
                # Create the boundary pattern using the next languages
                boundary_parts = [f"(?:{next_lang.title()}|{next_lang.upper()})" for next_lang in next_langs if next_lang]
                if boundary_parts:
                    boundary = f"(?=(?:{'|'.join(boundary_parts)}|$))"
                else:
                    boundary = "(?=$)"
            else:
                boundary = "(?=$)"
                
            # Create the pattern for this language
            pattern = f"(?:{lang_name.title()}|{lang_name.upper()})[:\s]+(.*?){boundary}"
            patterns[lang_name] = pattern
        
        for lang, pattern in patterns.items():
            match = re.search(pattern, response_text, re.DOTALL)
            if match:
                localization[lang] = match.group(1).strip()
            else:
                print(f"Warning: Could not extract {lang} localization")
                localization[lang] = f"Error: Could not extract {lang} localization"
        
        # Process output format and apply character name replacements if needed
        for lang_code in languages:
            lang_name = LANGUAGE_NAMES.get(lang_code.upper(), "").lower()
            if lang_name in localization:
                # Remove the "Localization:**\n\n" prefix and any explanations that follow the translated text
                text = localization[lang_name]
                
                # First, check if it has the format pattern
                if "Localization:**" in text:
                    # Remove the prefix
                    text = re.sub(r'Localization:\*\*\n\n', '', text)
                    
                    # Extract just the actual translation (everything before Explanation or end of string)
                    explanation_match = re.search(r'(\*\*Explanation:|\n\n\*\*Explanation:)', text)
                    if explanation_match:
                        text = text[:explanation_match.start()].strip()
                        
                # Apply character name replacements if character lookup is provided
                if char_lookup:
                    text = replace_character_names(text, lang_name, char_lookup)
                    
                # Update the localization with clean text
                localization[lang_name] = text
        
        print("✓ Successfully processed localizations")
        return localization
        
    except Exception as e:
        print(f"✗ Error processing localization: {str(e)}")
        return {
            "english": english_text,
            "turkish": f"Error: {str(e)}",
            "french": f"Error: {str(e)}",
            "german": f"Error: {str(e)}"
        }

def read_csv_file(csv_file):
    """Read CSV file and return rows"""
    rows = []
    try:
        with open(csv_file, 'r', encoding='utf-8-sig') as file:
            reader = csv.reader(file, delimiter=';')
            headers = next(reader)
            
            # Check if the CSV has the required columns
            required_columns = ['IDS', 'EN', 'LOCID']
            if not all(col in headers for col in required_columns):
                raise ValueError(f"CSV file must have columns: {required_columns}")
            
            # Get column indices
            ids_idx = headers.index('IDS')
            en_idx = headers.index('EN')
            locid_idx = headers.index('LOCID')
            
            for row in reader:
                if len(row) >= max(ids_idx, en_idx, locid_idx) + 1:
                    # Create a simple dict with just the required fields
                    row_dict = {
                        'IDS': row[ids_idx],
                        'EN': row[en_idx],
                        'LOCID': row[locid_idx]
                    }
                    rows.append(row_dict)
        
        print(f"✓ Successfully read CSV file: {csv_file}")
        print(f"  Rows: {len(rows)}")
        return rows
    except Exception as e:
        print(f"✗ Error reading CSV file: {str(e)}")
        return []

def process_csv_data(csv_data, images_dir, chars_file=None, model="grok3", languages=None, api_key=None, debug=False, skip_images=False, custom_prompt=None):
    """Process CSV data and generate localization results"""
    # Default languages if none provided
    if languages is None:
        languages = ["TR", "FR", "DE"]
    # Load character data if a file is provided
    char_lookup = None
    if chars_file:
        char_lookup = load_character_data(chars_file)
    
    # Group rows by image ID
    image_groups = {}
    for row in csv_data:
        image_id = row['IDS']
        if image_id not in image_groups:
            image_groups[image_id] = []
        image_groups[image_id].append(row)
    
    results = []
    
    # Process each image ID
    for image_id, rows in image_groups.items():
        print(f"\n📊 Processing image ID: {image_id}")
        
        # If skip_images is True or no images_dir was provided
        if skip_images or not images_dir:
            description = "ENTERED IMAGE FOLDER NOT SHOWN"
            filename = f"{image_id}.unknown"
            ocr_text = "[OCR text not available - no image directory specified]"
            print("⚠️ Skipping image processing, no valid images directory provided.")
        else:
            # Find image file in directory
            image_path = find_image_by_id(images_dir, image_id)
            if image_path:
                print(f"✓ Found image at: {image_path}")
                filename = os.path.basename(image_path)
                
                # Get image description
                try:
                    # Fixed function call to match the function signature
                    description = get_image_description(image_path, api_key, debug)
                    print(f"📝 Image description: {description[:100]}...")
                except Exception as e:
                    print(f"✗ Error getting image description: {str(e)}")
                    description = f"ERROR GETTING IMAGE DESCRIPTION: {str(e)}"
                
                # We're deliberately skipping actual OCR to avoid dependency issues
                # In a production environment, you'd replace this with a working OCR solution
                ocr_text = "[OCR functionality disabled to avoid dependency issues]"
            else:
                print(f"✗ Could not find image for ID: {image_id}")
                description = "IMAGE NOT FOUND"
                filename = f"{image_id}.unknown"
                ocr_text = "[OCR text not available - image not found]"
        
        # Initialize the result object for this image
        image_result = {
            "filename": filename,
            "description": description,
            "OCR_EN": ocr_text
        }
        
        # Process each text item for this image
        for row in rows:
            locid = row['LOCID']
            english_text = row['EN']
            
            # Process localization for this text
            localization = process_localization(description, english_text, model, languages, debug, char_lookup, api_key, custom_prompt)
            
            # Add localization to the result
            result_entry = {"EN": english_text}
            
            # Add all requested languages to the result
            for lang_code in languages:
                lang_name = LANGUAGE_NAMES.get(lang_code.upper(), "").lower()
                if lang_name and lang_name in localization:
                    result_entry[lang_name] = localization[lang_name]
                elif lang_name:
                    result_entry[lang_name] = f"[No translation available for {lang_name}]"
            
            # Add the entry to the image result
            image_result[locid] = result_entry
            
            # Small delay to avoid rate limits
            if not debug:
                time.sleep(0.5)
        
        results.append(image_result)
    
    return results

def save_results_as_json(results, output_file):
    """Save results as JSON file"""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ Successfully saved JSON results to: {output_file}")
        return True
    except Exception as e:
        print(f"\n✗ Error saving JSON results: {str(e)}")
        return False

def save_results_as_csv(results, output_file):
    """Save results as CSV file"""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Flatten the results structure for CSV
        rows = []
        headers = ["filename", "image_id", "locid", "english", "turkish", "french", "german"]
        
        for result in results:
            filename = result["filename"]
            # Extract ID from filename (assuming format like BT4_Level4_ID1.png)
            match = re.search(r"ID(\d+)", filename)
            image_id = match.group(1) if match else ""
            
            # Add entries for each localization key (LEVEL_TEXT_1, HINT_1_1, etc.)
            for key, value in result.items():
                if key not in ["filename", "description", "OCR_EN"]:
                    rows.append([
                        filename,
                        image_id,
                        key,
                        value["EN"],
                        value["turkish"],
                        value["french"],
                        value["german"]
                    ])
        
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(headers)
            for row in rows:
                writer.writerow(row)
        
        print(f"\n✓ Successfully saved CSV results to: {output_file}")
        return True
    except Exception as e:
        print(f"\n✗ Error saving CSV results: {str(e)}")
        return False

def process_localization_csv(csv_file, images_dir, output_dir, chars_file=None, model="grok3", debug=False):
    """Process localization from CSV file"""
    print(f"\n🚀 Starting localization processing from CSV: {csv_file}")
    print(f"📊 Using model: {model} for translations")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Read CSV data
    csv_data = read_csv_file(csv_file)
    
    if not csv_data:
        print("✗ No data to process. Exiting.")
        return False
    
    # Process CSV data and get results
    results = process_csv_data(csv_data, images_dir, chars_file, model, debug)
    
    if not results:
        print("✗ No results were generated. Nothing to save.")
        return False
    
    # Generate timestamped output filenames
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    json_output = os.path.join(output_dir, f"localization_results_{timestamp}.json")
    csv_output = os.path.join(output_dir, f"localization_results_{timestamp}.csv")
    
    # Save results as JSON and CSV
    json_saved = save_results_as_json(results, json_output)
    csv_saved = save_results_as_csv(results, csv_output)
    
    print("\n✅ Localization processing complete!")
    return json_saved and csv_saved

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Multi-Model Game Localization Tool with CSV Input")
    parser.add_argument("--csv_file", help="Path to the CSV file with localization data", required=True)
    parser.add_argument("--images_dir", help="Directory containing game screenshots", required=True)
    parser.add_argument("--output_dir", help="Directory to save output files", default="./output")
    parser.add_argument("--chars_file", help="Path to the JSON file with character name localizations", default=None)
    parser.add_argument("--model", help="Translation model to use (grok3, gpt-4o, claude-3-7-sonnet, gemini-1.5-pro)", default="grok3", 
                        choices=["grok3", "gpt-4o", "claude-3-7-sonnet", "gemini-1.5-pro"])
    parser.add_argument("--debug", help="Run in debug mode without calling API", action="store_true")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Process localization from CSV
    process_localization_csv(
        args.csv_file, 
        args.images_dir, 
        args.output_dir, 
        args.chars_file, 
        args.model,
        args.debug
    )

if __name__ == "__main__":
    main()

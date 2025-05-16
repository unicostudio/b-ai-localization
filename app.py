import os
import io
import json
import csv
import shutil
import zipfile
import configparser
import secrets
import threading
import time
import pandas as pd
import re
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_from_directory, make_response, send_file
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, emit
from minimal_localization_tool import read_csv_file, process_csv_data, load_character_data, LANGUAGE_CODES

app = Flask(__name__)
app.secret_key = "localization_tool_secret_key"
# Increase session lifetime and size limit
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours
app.config['SESSION_TYPE'] = 'filesystem'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['OUTPUT_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
# Enable CORS for SocketIO and set session handling
socketio = SocketIO(app, manage_session=True, cors_allowed_origins='*')

# Global variable to store the latest processing results
# This ensures we don't depend solely on session data
GLOBAL_EXPORT_DATA = {
    'results': [],
    'languages': {},
    'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S')
}

# Create upload and output folders if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Import zipfile for creating ZIP archives
import zipfile
import io

def allowed_file(filename):
    """Check if the file has an allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'csv'}

def validate_csv_format(file_path):
    """Validate that the CSV file has the required columns"""
    try:
        # Multiple attempts with different separators/parsers to ensure we can load the file
        dfs = []
        exceptions = []
        
        # Try various parsing methods
        parsing_methods = [
            # Try semicolon separator first (like in example.csv)
            lambda: pd.read_csv(file_path, sep=';', encoding='utf-8', engine='python'),
            # Try comma separator
            lambda: pd.read_csv(file_path, sep=',', encoding='utf-8', engine='python'),
            # Try with automatic separator detection
            lambda: pd.read_csv(file_path, sep=None, engine='python'),
            # Try with tab separator
            lambda: pd.read_csv(file_path, sep='\t', encoding='utf-8', engine='python'),
        ]
        
        # Try each parsing method
        for method in parsing_methods:
            try:
                df = method()
                if not df.empty and len(df.columns) > 1:  # Ensure we got meaningful data
                    dfs.append(df)
                    break  # Stop if we successfully parsed the file
            except Exception as e:
                exceptions.append(str(e))
        
        # If none of the above methods worked, try sniffing the dialect
        if not dfs:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    # Read a sample to detect dialect
                    sample = f.read(4096)  # Read a larger sample
                    f.seek(0)
                    
                    # Try to sniff the dialect
                    try:
                        dialect = csv.Sniffer().sniff(sample)
                        reader = csv.reader(f, dialect)
                        headers = next(reader)
                        rows = list(reader)
                        df = pd.DataFrame(rows, columns=headers)
                        dfs.append(df)
                    except Exception as e:
                        # If sniffing failed, try a direct read with semicolon
                        f.seek(0)
                        reader = csv.reader(f, delimiter=';')
                        headers = next(reader)
                        rows = list(reader)
                        df = pd.DataFrame(rows, columns=headers)
                        dfs.append(df)
            except Exception as e:
                exceptions.append(f"Dialect detection failed: {str(e)}")
        
        # If we still don't have any dataframes, raise an error
        if not dfs:
            error_messages = "\n".join(exceptions)
            return False, f"Failed to parse CSV file with any method. Errors: {error_messages}"
        
        # Use the first successfully parsed dataframe
        df = dfs[0]
        
        # Print column names for debugging
        print(f"CSV columns found: {list(df.columns)}")
        
        # Check for required columns (case insensitive)
        required_columns = ['IDS', 'EN', 'LOCID']
        
        # Normalize column names by stripping whitespace and converting to uppercase
        normalized_columns = [col.strip().upper() for col in df.columns]
        
        # Check each required column
        for col in required_columns:
            if col.upper() not in normalized_columns:
                return False, f"Missing required column: {col}"
        
        return True, "CSV format is valid"
    except Exception as e:
        return False, f"Error validating CSV: {str(e)}"

# Create a static folder for JavaScript files
static_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
os.makedirs(static_folder, exist_ok=True)

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(static_folder, filename)

@app.route('/get_available_languages')
def get_available_languages():
    """API endpoint to get available languages for export"""
    try:
        # First check the global variable, which is the most reliable source
        global GLOBAL_EXPORT_DATA
        if GLOBAL_EXPORT_DATA and 'languages' in GLOBAL_EXPORT_DATA and GLOBAL_EXPORT_DATA['languages']:
            print(f"Using global export data with languages: {list(GLOBAL_EXPORT_DATA['languages'].keys())}")
            return jsonify({'success': True, 'languages': GLOBAL_EXPORT_DATA['languages']})
            
        # If global data is empty, try session
        export_data = None
        if 'export_data' in session:
            try:
                export_data = session.get('export_data')
                print(f"Retrieved export data from session")
                # Update global data for future use
                GLOBAL_EXPORT_DATA = export_data
            except Exception as e:
                print(f"Error retrieving from session: {str(e)}")
                export_data = None
        
        # If no session data, try to find backup files
        if not export_data:
            try:
                export_files = [f for f in os.listdir(app.config['OUTPUT_FOLDER']) if f.startswith('export_data_')]
                
                if export_files:
                    # Sort by name (timestamp) to get the most recent one
                    latest_file = sorted(export_files)[-1]
                    try:
                        with open(os.path.join(app.config['OUTPUT_FOLDER'], latest_file), 'r', encoding='utf-8') as f:
                            export_data = json.load(f)
                            # Update both session and global data
                            session['export_data'] = export_data
                            GLOBAL_EXPORT_DATA = export_data
                            session.modified = True
                            print(f"Loaded and cached export data from backup file: {latest_file}")
                    except Exception as e:
                        print(f"Error loading backup file: {str(e)}")
            except Exception as e:
                print(f"Error searching for backup files: {str(e)}")
        
        # If we have export data, return languages
        if export_data and 'languages' in export_data:
            return jsonify({'success': True, 'languages': export_data['languages']})
        
        # If all else fails, use hard-coded default languages for testing
        # These are just to ensure the UI shows something usable
        default_langs = {
            'TR': 'turkish',
            'FR': 'french',
            'DE': 'german'
        }
        print("Using default languages as fallback")
        return jsonify({'success': True, 'languages': default_langs})
    except Exception as e:
        print(f"Error in get_available_languages: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/browse_directory')
def browse_directory():
    """API endpoint to browse directories on the server"""
    current_path = request.args.get('path', os.path.expanduser('~'))
    
    try:
        # Make sure the path exists and is a directory
        if not os.path.exists(current_path) or not os.path.isdir(current_path):
            current_path = os.path.expanduser('~')
        
        # Get all directories and files in the current path
        items = []
        for item in os.listdir(current_path):
            item_path = os.path.join(current_path, item)
            is_dir = os.path.isdir(item_path)
            items.append({
                'name': item,
                'path': item_path,
                'is_dir': is_dir
            })
        
        # Sort directories first, then files
        items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
        
        # Get parent directory
        parent_dir = os.path.dirname(current_path)
        
        return jsonify({
            'current_path': current_path,
            'parent_dir': parent_dir,
            'items': items
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/browse_files')
def browse_files():
    """API endpoint to browse files on the server with filtering"""
    current_path = request.args.get('path', os.path.expanduser('~'))
    file_type = request.args.get('file_type', 'json')
    
    try:
        # Make sure the path exists and is a directory
        if not os.path.exists(current_path) or not os.path.isdir(current_path):
            current_path = os.path.expanduser('~')
        
        # Get all directories and files in the current path
        items = []
        for item in os.listdir(current_path):
            item_path = os.path.join(current_path, item)
            is_dir = os.path.isdir(item_path)
            
            # Only include directories and files with matching extension
            if is_dir or (os.path.isfile(item_path) and item.lower().endswith('.' + file_type.lower())):
                items.append({
                    'name': item,
                    'path': item_path,
                    'is_dir': is_dir
                })
        
        # Sort directories first, then files
        items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
        
        # Get parent directory
        parent_dir = os.path.dirname(current_path)
        
        return jsonify({
            'current_path': current_path,
            'parent_dir': parent_dir,
            'items': items
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    # If it's a GET request, redirect to the home page
    if request.method == 'GET':
        return redirect(url_for('index'))
    if 'csv_file' not in request.files:
        flash('No file part', 'danger')
        return redirect(request.url)
    
    csv_file = request.files['csv_file']
    if csv_file.filename == '':
        flash('No selected file', 'danger')
        return redirect(request.url)
    
    if not allowed_file(csv_file.filename):
        flash('Invalid file type. Please upload a CSV file.', 'danger')
        return redirect(request.url)
    
    # Save the uploaded CSV file
    csv_filename = secure_filename(csv_file.filename)
    csv_path = os.path.join(app.config['UPLOAD_FOLDER'], csv_filename)
    csv_file.save(csv_path)
    
    # Validate CSV format
    is_valid, message = validate_csv_format(csv_path)
    if not is_valid:
        os.remove(csv_path)  # Remove invalid file
        flash(message, 'danger')
        return redirect(url_for('index'))
    
    # Store file path in session for processing
    full_csv_path = os.path.abspath(csv_path)
    session['csv_path'] = full_csv_path
    print(f"CSV file saved to: {full_csv_path}")
    
    flash(f"CSV file '{csv_filename}' uploaded successfully!", 'success')
    return redirect(url_for('index'))

@app.route('/process', methods=['GET', 'POST'])
def process():
    # If it's a GET request, redirect to the home page
    if request.method == 'GET':
        return redirect(url_for('index'))
    # Get form data
    images_dir = request.form.get('images_dir', '')
    chars_file = request.form.get('chars_file', '')
    model = request.form.get('model', 'grok3')
    api_key = request.form.get('api_key', '')
    debug_mode = 'debug_mode' in request.form
    
    # Validate OpenRouter API key format if provided and not in debug mode
    if api_key and not debug_mode:
        # OpenRouter API keys typically start with sk-or-v1-
        openrouter_pattern = r'^sk-or-v[0-9]+-[a-zA-Z0-9]{40,}$'
        if not re.match(openrouter_pattern, api_key):
            flash('Invalid OpenRouter API key format. API keys should start with sk-or-v1- followed by a long string of characters.', 'danger')
            return redirect(url_for('index'))
    
    # Get selected languages (default to Turkish, French, German if none selected)
    selected_languages = request.form.getlist('languages[]')
    if not selected_languages:
        selected_languages = ['TR', 'FR', 'DE']
        print("No languages selected, defaulting to TR, FR, DE")
    else:
        print(f"Selected languages: {selected_languages}")
        
    # Get selected output formats (default to allOutput if none selected)
    selected_formats = request.form.getlist('output_formats[]')
    if not selected_formats:
        selected_formats = ['allOutput']
        print("No output formats selected, defaulting to allOutput")
    else:
        print(f"Selected output formats: {selected_formats}")
    
    # Use the provided API key if available
    if api_key:
        print("Using custom API key")
    else:
        print("No API key provided, using environment variable if available")
    
    # If chars_file is empty, use the default chars.json in the same directory
    if not chars_file:
        default_chars_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chars.json')
        if os.path.exists(default_chars_file):
            chars_file = default_chars_file
            print(f"Using default characters file: {chars_file}")
        else:
            print("Default characters file not found, proceeding without character replacements")
    
    # Check for empty or invalid images directory - but make it optional
    skip_images = False
    if not images_dir or not os.path.isdir(images_dir):
        # Store status in session for warning
        session['image_warning'] = True
        session['warning_message'] = 'Images directory not specified or does not exist.'
        session['image_dir_valid'] = False
        skip_images = True
        # Don't return/redirect - just warn during processing
        print(f"Warning: Images directory not specified or invalid: '{images_dir}'")
    else:
        session['image_dir_valid'] = True
        session['image_warning'] = False
    
    # Check characters file, but make it optional and use default if not provided
    if chars_file and not os.path.isfile(chars_file):
        # Specified file doesn't exist - try using default
        flash('Specified characters file does not exist, will try using default chars.json', 'warning')
        chars_file = None  # Reset to use default later
    
    # Get CSV path from session
    csv_path = session.get('csv_path', '')
    
    # Check if CSV path is valid and file exists
    if not csv_path:
        flash('No CSV file found in session. Please upload a CSV file first.', 'danger')
        return redirect(url_for('index'))
        
    # Verify the file still exists
    if not os.path.exists(csv_path):
        flash(f'CSV file not found at path: {csv_path}. Please upload the file again.', 'danger')
        # Clear the invalid session data
        session.pop('csv_path', None)
        return redirect(url_for('index'))
    
    # Get custom prompt and game selection (new in Step 7)
    custom_prompt = request.form.get('custom_prompt', '')
    game_selection = request.form.get('game_selection', 'brain-test-1')
    
    # Store processing parameters in session
    session['processing'] = {
        'csv_path': csv_path,
        'images_dir': images_dir,
        'chars_file': chars_file,
        'model': model,
        'languages': selected_languages,
        'api_key': api_key,
        'debug_mode': debug_mode,
        'skip_images': skip_images,
        'output_formats': selected_formats,  # Store the selected output formats
        'custom_prompt': custom_prompt,      # Store the custom prompt
        'game_selection': game_selection     # Store the game selection
    }
    
    return redirect(url_for('processing'))

@app.route('/processing')
def processing():
    if 'processing' not in session:
        return redirect(url_for('index'))
    
    # Get API key from session if available
    processing_data = session.get('processing', {})
    api_key = processing_data.get('api_key', '')
    debug_mode = processing_data.get('debug_mode', False)
    
    # Only pass the API key if not in debug mode
    api_key_for_template = '' if debug_mode else api_key
    
    return render_template('processing.html', api_key=api_key_for_template)

@app.route('/check_openrouter_limits', methods=['GET'])
def check_openrouter_limits():
    """Check OpenRouter API key limits"""
    try:
        api_key = request.args.get('api_key', '')
        
        if not api_key:
            return jsonify({
                'success': False,
                'error': 'No API key provided'
            })
        
        # Make request to OpenRouter API to get key info
        response = requests.get(
            url="https://openrouter.ai/api/v1/auth/key",
            headers={
                "Authorization": f"Bearer {api_key}"
            }
        )
        
        # Check if request was successful
        if response.status_code == 200:
            key_data = response.json()
            return jsonify({
                'success': True,
                'data': key_data
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Error fetching key information: {response.status_code}',
                'message': response.text
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error: {str(e)}'
        })

@socketio.on('check_image_warning')
def handle_image_warning_check(data=None):
    warning = session.get('image_warning', False)
    valid = session.get('image_dir_valid', True)
    message = session.get('warning_message', '')
    
    emit('image_warning_status', {
        'warning': warning,
        'valid': valid,
        'message': message
    })

@socketio.on('start_processing')
def handle_start_processing(data=None):
    try:
        # Check if processing is already in progress or completed
        if session.get('processing_status') == 'in_progress':
            emit('update_status', {
                'status': 'Processing already in progress',
            })
            return
        
        # Set processing status to in_progress
        session['processing_status'] = 'in_progress'
        session.modified = True
        
        # Default to not skipping images
        skip_images = False
        if data and 'skip_images' in data:
            skip_images = data['skip_images']
        
        # Get process parameters from session
        params = session.get('processing', {})
        csv_path = params.get('csv_path', '')
        images_dir = params.get('images_dir', '')
        chars_file = params.get('chars_file', '')
        model = params.get('model', 'grok3')
        languages = params.get('languages', ['TR', 'FR', 'DE'])
        api_key = params.get('api_key', '')
        debug_mode = params.get('debug_mode', False)
        custom_prompt = params.get('custom_prompt', '')
        game_selection = params.get('game_selection', 'brain-test-1')
        
        # Print session data for debugging
        print(f"Session data during processing: {session.get('processing')}")
        print(f"CSV path from session: {csv_path}")
        
        # Check if CSV path exists and is valid
        if not csv_path:
            emit('update_status', {
                'status': 'Error: No CSV file uploaded yet. Please go back and upload a CSV file first.', 
                'error': True,
                'message': 'If you downloaded the example.csv file, you still need to upload it using the "Upload CSV" button.'
            })
            return
        
        if not os.path.isfile(csv_path):
            emit('update_status', {
                'status': f'Error: CSV file not found at path: {csv_path}', 
                'error': True,
                'message': 'The CSV file may have been moved or deleted. Please upload it again.'
            })
            return
        
        # Always use example_chars.json as the default character file
        # Try to use explicitly specified chars file first
        if chars_file and os.path.isfile(chars_file):
            emit('update_status', {'status': f'Using specified characters file: {chars_file}'})
        else:
            # Look for example_chars.json in the app directory
            example_chars_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'example_chars.json')
            if os.path.exists(example_chars_file):
                chars_file = example_chars_file
                emit('update_status', {'status': f'Using example character file: {chars_file}'})
            else:
                # Fall back to chars.json if example_chars.json doesn't exist
                default_chars_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chars.json')
                if os.path.exists(default_chars_file):
                    chars_file = default_chars_file
                    emit('update_status', {'status': f'Using fallback character file: {chars_file}'})
                else:
                    emit('update_status', {'status': 'Warning: No character file found. Character names will not be localized correctly.'})
                    chars_file = None
        
        emit('update_status', {'status': 'Reading CSV file...'})
        
        # Read CSV file 
        csv_data = read_csv_file(csv_path)
        if not csv_data:
            emit('update_status', {'status': 'Error: Failed to read CSV file.', 'error': True})
            return
        
        emit('update_status', {'status': f'Processing {len(csv_data)} entries...'})
        
        # Process data
        emit('update_status', {'status': f'Using model: {model} for translations...'})
        emit('update_status', {'status': f'Selected languages: {", ".join(languages)}'})
        if api_key:
            emit('update_status', {'status': 'Using provided API key'})
            
        # Add skip_images parameter to process_csv_data
        if skip_images:
            emit('update_status', {'status': 'No image directory specified. Proceeding with text-only localization...'})
            # Set images_dir to None to skip image processing
            images_dir = None
            
        # Process data
        emit('update_status', {'status': f'Using game profile: {game_selection.replace("-", " ").title()}'})
        if custom_prompt:
            emit('update_status', {'status': 'Using custom prompt for localization'})
        
        # Process data with custom prompt
        results = process_csv_data(csv_data, images_dir, chars_file, model, languages, api_key, debug_mode, skip_images, custom_prompt=custom_prompt)
        if not results:
            emit('update_status', {'status': 'Error: Failed to process data.', 'error': True})
            return
        
        # Generate timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Get selected output formats
        params = session.get('processing', {})
        output_formats = params.get('output_formats', ['allOutput'])  # Default to allOutput
        print(f"Output formats selected: {output_formats}")
        
        # Initialize paths
        json_output_path = None
        csv_output_path = None
        
        # Create complete output.json if 'allOutput' format is selected
        json_memory_file = None
        if 'allOutput' in output_formats:
            # Create JSON in memory instead of saving to disk
            json_data = json.dumps(results, ensure_ascii=False, indent=2)
            json_memory_file = io.BytesIO(json_data.encode('utf-8'))
            json_output_path = f'output_{timestamp}.json'  # Just store the filename, not the path
            
            # Store the memory file in the session for download
            if 'memory_files' not in session:
                session['memory_files'] = {}
            session['memory_files'][json_output_path] = json_memory_file.getvalue()
            session.modified = True
            
            # Also save to disk as a backup
            disk_path = os.path.join(app.config['OUTPUT_FOLDER'], json_output_path)
            with open(disk_path, 'wb') as f:
                f.write(json_memory_file.getvalue())
            
            print(f"Created output.json file (memory + disk backup at {disk_path})")
        
        # Store language codes for export
        languages_list = {}
        for lang_code in languages:
            lang_name = next((k for k, v in LANGUAGE_CODES.items() if v.upper() == lang_code.upper()), lang_code.lower())
            languages_list[lang_code] = lang_name
        
        # Store results and language info in both session and global variable for export
        export_data = {
            'results': results,
            'languages': languages_list,
            'timestamp': timestamp
        }
        
        # Update session
        session['export_data'] = export_data
        session.modified = True
        
        # Update global variable
        global GLOBAL_EXPORT_DATA
        GLOBAL_EXPORT_DATA = export_data
        print(f"Updated global export data with languages: {list(languages_list.keys())}")
        
        # Also save a backup of the export data to a file for redundancy
        export_data_file = os.path.join(app.config['OUTPUT_FOLDER'], f'export_data_{timestamp}.json')
        with open(export_data_file, 'w', encoding='utf-8') as f:
            # We need to convert the data to be JSON serializable
            json_safe_data = {
                'results': results,
                'languages': languages_list,
                'timestamp': timestamp
            }
            json.dump(json_safe_data, f, ensure_ascii=False, indent=2)
        
        # Create CSV output only if allOutput format is selected
        if 'allOutput' in output_formats and csv_output_path:
            csv_rows = []
            
            for item in results:
                filename = item.get('filename', 'unknown')
                ocr_en = item.get('OCR_EN', '')
                
                # Add each localization to a row
                for key, loc_data in item.items():
                    if key.startswith('LEVEL_TEXT_') or key.startswith('HINT_') or key.startswith('END_'):
                        row = {
                            'FILENAME': filename,
                            'LOCID': key,
                            'EN': loc_data.get('english', ''),
                            'TR': loc_data.get('turkish', ''),
                            'FR': loc_data.get('french', ''),
                            'DE': loc_data.get('german', '')
                        }
                        csv_rows.append(row)
            
            # Convert to DataFrame and save
            if csv_rows:
                df = pd.DataFrame(csv_rows)
                df.to_csv(csv_output_path, index=False, encoding='utf-8')
                print(f"Saved CSV output to {csv_output_path}")
            

        
        # Initialize zip variables
        zip_path = None
        zip_filename = None
        
        # Create language-specific JSON files and package them in a ZIP if the format is selected
        zip_memory_file = None
        if 'allbyLang' in output_formats or 'third' in output_formats:
            try:
                # Create a ZIP file for language-specific JSONs
                zip_memory_file = create_language_specific_json_files(results, languages)
                zip_filename = f"localized_strings_{timestamp}.zip"
                
                # Store the memory file in the session for download
                if 'memory_files' not in session:
                    session['memory_files'] = {}
                session['memory_files'][zip_filename] = zip_memory_file.getvalue()
                session.modified = True
                
                # Also save to disk as a backup
                disk_path = os.path.join(app.config['OUTPUT_FOLDER'], zip_filename)
                with open(disk_path, 'wb') as f:
                    f.write(zip_memory_file.getvalue())
                
                # Set the path variable to just the filename for reference
                zip_path = zip_filename
                
                print(f"Created language-specific JSON files (memory + disk backup at {disk_path})")
                
            except Exception as e:
                print(f"Error creating language-specific JSON files: {str(e)}")
                zip_path = None
                zip_filename = None
        
        # Send success message with file paths for all generated formats
        response_data = {
            'status': 'Processing completed successfully!',
            'complete': True,
            'output_formats': output_formats
        }
        
        # Mark processing as completed
        session['processing_status'] = 'completed'
        session.modified = True
        
        # Add paths to the response if they were created
        if json_output_path:
            response_data['json_path'] = json_output_path
        if csv_output_path:
            response_data['csv_path'] = csv_output_path
        if zip_path:
            response_data['zip_path'] = zip_path
            response_data['zip_filename'] = zip_filename
            
        emit('update_status', response_data)
        
    except Exception as e:
        print(f"Error in process_uploads: {str(e)}")
        # Report the error
        emit('update_status', {
            'status': f'Error during processing: {str(e)}',
            'complete': True,
            'error': True
        })

# Function to create language-specific JSON files
def create_language_specific_json_files(results, languages):
    """
    Create separate JSON files for each language and package them into a ZIP file.
    Formats keys according to standard mapping and excludes custom_description.
    
    Args:
        results: List of processed localization entries
        languages: List of language codes to include
        
    Returns:
        BytesIO object containing the ZIP file
    """
    print(f"Creating language-specific JSON files for: {languages}")
    memory_file = io.BytesIO()
    
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Process each language
        for lang_code in languages:
            # Get language name from code
            lang_name = next((k for k, v in LANGUAGE_CODES.items() if v.upper() == lang_code.upper()), lang_code.lower())
            print(f"Processing language: {lang_code} ({lang_name})")
            
            # Create export for this language
            flat_export = {}
            
            # Process all results
            for item in results:
                # Process each key in the item
                for key, loc_data in item.items():
                    # Skip metadata fields and custom_description
                    if key in ('ID', 'id', 'filename', 'OCR_EN', 'image_path', 'image_description', 'description'):
                        continue
                    
                    # Format the key according to LOCID type
                    formatted_key = None
                    
                    # Handle standard prefixes with correct multi-level ID formatting
                    if key.startswith('LEVEL_TEXT_'):
                        parts = key.replace('LEVEL_TEXT_', '').split('_')
                        formatted_key = f"question_{parts[0]}"
                        if len(parts) > 1:
                            formatted_key += '_' + '_'.join(parts[1:])
                    elif key.startswith('HINT_'):
                        parts = key.replace('HINT_', '').split('_')
                        formatted_key = f"hint_{parts[0]}"
                        if len(parts) > 1:
                            formatted_key += '_' + '_'.join(parts[1:])
                    elif key.startswith('END_'):
                        parts = key.replace('END_', '').split('_')
                        formatted_key = f"endText_{parts[0]}"
                        if len(parts) > 1:
                            formatted_key += '_' + '_'.join(parts[1:])
                    else:
                        # Skip custom_description
                        if key == 'custom_description' or key.lower() == 'description':
                            continue
                        # For any other LOCID, use custom prefix but not for descriptions
                        formatted_key = f"custom_{key}"
                    
                    # Get translation for this language
                    translation = ""
                    if isinstance(loc_data, dict):
                        # Try different ways to get the translation
                        if lang_name.lower() in loc_data:
                            translation = loc_data[lang_name.lower()]
                        elif lang_code.lower() in loc_data:
                            translation = loc_data[lang_code.lower()]
                        else:
                            # Try to find a matching key
                            for k in loc_data.keys():
                                if lang_name.lower() in k.lower() or lang_code.lower() in k.lower():
                                    translation = loc_data[k]
                                    break
                                elif k.lower() == 'english' and lang_code.upper() == 'EN':
                                    translation = loc_data[k]
                                    break
                        
                        # Skip empty or error translations
                        if translation and (translation.startswith('[No translation') or translation.startswith('Error:')):
                            translation = ""
                    
                    # Add to our export if we have a formatted key
                    if formatted_key and formatted_key != "custom_description":
                        flat_export[formatted_key] = translation
                        
            # Create JSON content for this language
            json_content = json.dumps(flat_export, ensure_ascii=False, indent=2)
            
            # Add to ZIP with appropriate filename
            filename = f"strings_{lang_code.lower()}.json"
            zf.writestr(filename, json_content)
            print(f"Added {filename} to ZIP with {len(flat_export)} entries")
    
    # Reset file pointer and return
    memory_file.seek(0)
    return memory_file

# New language-based export functionality
@app.route('/download_all_by_lang', methods=['POST'])
def download_all_by_lang():
    """Download all selected languages as separate JSON files in a ZIP archive"""
    print("\n=== DOWNLOAD ALL BY LANG ENDPOINT CALLED ===\n")
    print(f"REQUEST: {request.method} {request.path}")
    print(f"Content-Type: {request.headers.get('Content-Type')}")
    print(f"Accept: {request.headers.get('Accept')}")
    
    # Get selected languages from form data
    selected_languages = request.form.get('languages', 'TR,FR,DE')
    selected_lang_codes = [code.strip() for code in selected_languages.split(',') if code.strip()]
    print(f"Received language selection for download: {selected_lang_codes}")
    
    try:
        # Get export data from various sources
        export_data = None
        
        # First try global data
        global GLOBAL_EXPORT_DATA
        if GLOBAL_EXPORT_DATA and 'results' in GLOBAL_EXPORT_DATA:
            export_data = GLOBAL_EXPORT_DATA
            print(f"Using global data with languages: {list(export_data.get('languages', {}).keys())}")
            
        # Try session data if needed
        if not export_data and 'export_data' in session:
            try:
                export_data = session.get('export_data')
                print(f"Using session data")
            except Exception as e:
                print(f"Error getting session data: {str(e)}")
                
        # If still no data, try to find export files
        if not export_data:
            try:
                export_files = [f for f in os.listdir(app.config['OUTPUT_FOLDER']) if f.startswith('export_data_')]
                if export_files:
                    latest_file = sorted(export_files)[-1]
                    print(f"Found backup file: {latest_file}")
                    try:
                        with open(os.path.join(app.config['OUTPUT_FOLDER'], latest_file), 'r', encoding='utf-8') as f:
                            export_data = json.load(f)
                            print(f"Loaded backup file with languages: {list(export_data.get('languages', {}).keys())}")
                    except Exception as e:
                        print(f"Error loading backup file: {str(e)}")
            except Exception as e:
                print(f"Error searching for backup files: {str(e)}")
        
        # If no data found, show error
        if not export_data or 'results' not in export_data:
            error_msg = 'No export data available. Please process data first.'
            print(error_msg)
            return make_response(error_msg, 400)
        
        # Get output.json directly from uploads folder (newest one)
        output_files = sorted([f for f in os.listdir(app.config['UPLOAD_FOLDER']) if f.startswith('output_') and f.endswith('.json')], reverse=True)
        
        if output_files:
            newest_output = output_files[0]
            output_path = os.path.join(app.config['UPLOAD_FOLDER'], newest_output)
            print(f"Found output.json file: {output_path}")
            
            try:
                # Load the complete output.json file to ensure we have all entries
                with open(output_path, 'r', encoding='utf-8') as f:
                    complete_results = json.load(f)
                    print(f"Loaded complete output.json with {len(complete_results)} entries")
            except Exception as e:
                print(f"Error loading output.json: {str(e)}")
                complete_results = export_data.get('results', [])
        else:
            complete_results = export_data.get('results', [])
        
        # Get timestamp and language data
        timestamp = export_data.get('timestamp', datetime.now().strftime('%Y%m%d_%H%M%S'))
        languages = export_data.get('languages', {})
        
        # If no languages found, use defaults
        if not languages:
            print("No languages found in data, using selected languages")
            languages = {}
            for lang_code in selected_lang_codes:
                # Map language codes to names
                if lang_code == 'TR':
                    languages[lang_code] = 'turkish'
                elif lang_code == 'FR':
                    languages[lang_code] = 'french'
                elif lang_code == 'DE':
                    languages[lang_code] = 'german'
                elif lang_code == 'EN':
                    languages[lang_code] = 'english'
                else:
                    languages[lang_code] = lang_code.lower()
        
        # Create ZIP file with individual JSON files per language
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Filter to only selected languages
            filtered_languages = {}
            for lang_code, lang_name in languages.items():
                if lang_code in selected_lang_codes:
                    filtered_languages[lang_code] = lang_name
            
            print(f"Creating exports for languages: {list(filtered_languages.keys())}")
            
            # If no languages match, use all available
            if not filtered_languages:
                filtered_languages = languages
                print(f"No matching languages found, using all: {list(filtered_languages.keys())}")
            
            # Process each language separately
            for lang_code, lang_name in filtered_languages.items():
                print(f"\nProcessing language: {lang_code} ({lang_name})")
                
                # Create export for this language
                flat_export = {}
                
                # Process all entries from the complete results
                entry_count = 0
                for item in complete_results:
                    item_id = item.get('ID', 'unknown')
                    
                    # Process each key in the item
                    for key, loc_data in item.items():
                        # Skip metadata fields and description
                        if key in ('ID', 'id', 'filename', 'OCR_EN', 'image_path', 'image_description', 'description'):
                            continue
                        
                        # Skip custom_description or any description fields
                        if key == 'custom_description' or 'description' in key.lower():
                            continue
                        
                        # Format the key according to LOCID type
                        formatted_key = None
                        
                        # Handle standard prefixes with correct multi-level ID formatting
                        if key.startswith('LEVEL_TEXT_'):
                            parts = key.replace('LEVEL_TEXT_', '').split('_')
                            formatted_key = f"question_{parts[0]}"
                            if len(parts) > 1:
                                formatted_key += '_' + '_'.join(parts[1:])
                        elif key.startswith('HINT_'):
                            parts = key.replace('HINT_', '').split('_')
                            formatted_key = f"hint_{parts[0]}"
                            if len(parts) > 1:
                                formatted_key += '_' + '_'.join(parts[1:])
                        elif key.startswith('END_'):
                            parts = key.replace('END_', '').split('_')
                            formatted_key = f"endText_{parts[0]}"
                            if len(parts) > 1:
                                formatted_key += '_' + '_'.join(parts[1:])
                        else:
                            # For any other LOCID, use custom prefix
                            formatted_key = f"custom_{key}"
                        
                        # Get translation for this language
                        translation = ""
                        if isinstance(loc_data, dict):
                            # Try different ways to get the translation
                            # First try with language name (most common)
                            if lang_name.lower() in loc_data:
                                translation = loc_data[lang_name.lower()]
                            # Next try with language code
                            elif lang_code.lower() in loc_data:
                                translation = loc_data[lang_code.lower()]
                            # Special case for English
                            elif lang_code.upper() == 'EN' and 'english' in loc_data:
                                translation = loc_data['english']
                            # Try finding a key that contains the language
                            else:
                                for k in loc_data.keys():
                                    if lang_name.lower() in k.lower() or lang_code.lower() in k.lower():
                                        translation = loc_data[k]
                                        break
                            
                            # Skip error or empty translations
                            if translation and (translation.startswith('[No translation') or translation.startswith('Error:')):
                                translation = ""
                        
                        # Add to our flat export structure if we have a formatted key
                        if formatted_key and formatted_key != "custom_description":
                            flat_export[formatted_key] = translation
                            entry_count += 1
                
                print(f"Added {entry_count} entries for language {lang_code}")
                
                # Create JSON content for this language
                json_content = json.dumps(flat_export, ensure_ascii=False, indent=2)
                
                # Add to ZIP with appropriate filename
                filename = f"strings_{lang_code.lower()}.json"
                zf.writestr(filename, json_content)
                print(f"Added {filename} to ZIP")
        
        # Reset file pointer and create response
        memory_file.seek(0)
        print("Memory file created successfully, preparing to send...")
        
        # Create response with the ZIP file
        try:
            response = send_file(
                memory_file,
                mimetype='application/zip',
                as_attachment=True,
                download_name=f"all_translations_{timestamp}.zip"
            )
            print(f"Successfully prepared ZIP file for download")
            return response
        except Exception as e:
            print(f"Error creating file response: {e}")
            return make_response(f"Error creating file response: {str(e)}", 500)
                
        # Add to ZIP with appropriate filename
        filename = f"strings_{lang_code.lower()}.json"
        zf.writestr(filename, json_content)
        print(f"Added {filename} to ZIP")

        # Reset file pointer and create response
        memory_file.seek(0)
        print("Memory file created successfully, preparing to send...")
        
        # Create response with the ZIP file
        try:
            response = send_file(
                memory_file,
                mimetype='application/zip',
                as_attachment=True,
                download_name=f"all_translations_{timestamp}.zip"
            )
            print(f"Successfully prepared ZIP file for download")
            return response
        except Exception as e:
            print(f"Error creating file response: {e}")
            return make_response(f"Error creating file response: {str(e)}", 500)
    
    except Exception as e:
        print(f"Error in download_all_by_lang: {str(e)}")
        error_message = f"Error preparing download: {str(e)}"
        return make_response(error_message, 500)

@app.route('/download')
def download_file():
    """Download a file from memory or disk"""
    file_path = request.args.get('file_path', '')
    print(f"Download requested for: {file_path}")
    
    # Get just the filename without the path
    if os.path.sep in file_path:
        filename = os.path.basename(file_path)
    else:
        filename = file_path  # Already just a filename
    
    # Try to get the file from session memory
    found_in_session = False
    if 'memory_files' in session and filename in session['memory_files']:
        try:
            # Create BytesIO object from the stored bytes
            file_data = session['memory_files'][filename]
            memory_file = io.BytesIO(file_data)
            memory_file.seek(0)
            found_in_session = True
            
            # Determine content type
            content_type = 'application/json'
            if filename.endswith('.zip'):
                content_type = 'application/zip'
            
            # Log the download
            print(f"Downloading in-memory file: {filename} (found in session)")
            
            # Create and return the response
            return send_file(
                memory_file,
                mimetype=content_type,
                as_attachment=True,
                download_name=filename
            )
        except Exception as e:
            print(f"Error retrieving from session: {str(e)}")
            found_in_session = False
    else:
        print(f"File not found in session memory: {filename}")

    # Try finding in output folder if not found in session
    disk_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    if os.path.exists(disk_path):
        print(f"Downloading file from disk (output folder): {disk_path}")
        return send_file(disk_path, as_attachment=True, download_name=filename)
    
    # Fallback to checking the exact path specified
    if os.path.exists(file_path):
        print(f"Downloading file from disk (fallback): {file_path}")
        return send_file(file_path, as_attachment=True, download_name=filename)
    
    # If file not found anywhere, return error
    error_msg = f"File not found. Checked session, output folder ({disk_path}), and full path ({file_path})"
    print(error_msg)
    flash('File not found', 'danger')
    return redirect(url_for('index'))

@app.route('/example_csv')
def example_csv():
    """Generate and serve an example CSV file"""
    # Create CSV content with sample data using semicolons as separators
    csv_content = """IDS;EN;LOCID
ID1;Tap on the biggest flower.;LEVEL_TEXT_1
ID1;Drag out the Sun behind Lily's head.;HINT_1_1
ID1;Tap on the biggest flower.;HINT_1_2
ID1;Awesome! Now tell me: What other game gives you a chance to move the Sun like this?;END_1_1
ID2;Lets find Tricky Lily;LEVEL_TEXT_2
ID2;Ohhh astrodog jimmy ;HINT_2_1
ID2;Doctor Worry dont worry?;END_2_1
ID3;I have always worry about the sky.;LEVEL_TEXT_3
ID3;Uncle where is the bubba.;HINT_3_1
ID3;Bubba by the way.;END_3_1
ID4;Little Little Tiki Taka;LEVEL_TEXT_4
ID4;Tiki is here;HINT_4
ID4;Layz Lary merry me;END_4
ID5;Lary not merry me;LEVEL_TEXT_5
ID5;where is the Martian?;HINT_5_1
ID5;The Martian is here;HINT_5_2
ID5;Martian is here ;HINT_5
ID5;Awesome! Now tell me: What other game gives you a chance to move the Sun like this?;END_5
ID6;Where is the sun?;LEVEL_TEXT_6
ID6;Where is the sun?;HINT_6
ID6;Where is the sun?;END_6
"""
    
    # Create response with CSV file
    response = make_response(csv_content)
    response.headers["Content-Type"] = "text/csv"
    response.headers["Content-Disposition"] = "attachment; filename=example.csv"
    
    return response

@app.route('/example_json')
def example_json():
    """Serve the example_chars.json file"""
    # Path to the example chars file
    example_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'example_chars.json')
    
    # Check if the file exists
    if os.path.exists(example_file):
        # Return the example chars file
        return send_from_directory(os.path.dirname(example_file), 
                                  os.path.basename(example_file),
                                  as_attachment=True, 
                                  download_name="example_chars.json")
    else:
        # If file doesn't exist, return a simple example JSON structure
        example_data = {
            {
    "Character Name (EN)": "Lily",
    "EN": "Lily",
    "AR": "ليلى المخادعة",
    "CN_TR": "俏皮莉莉",
    "CZ (cestina)": "Mazaná Lucka",
    "FR": "Lily Facétie",
    "DE": "Listige Lilli",
    "HU (magyar)": "Cseles Csenge",
    "ID": "Licca Liku",
    "IT": "Lilli la furba",
    "JP": "おしゃまなリリー",
    "KR": "교묘한 릴리",
    "MY": "Lily Licik",
    "PL (Polski)": "Przebiegła Lidka",
    "PT": "Lily Astuta",
    "RO": "Poznașa Lia",
    "RU": "Непоседа Лиля",
    "ES": "Lily la lista",
    "TH (Thai)": "สายฝนขี้แกล้ง",
    "TR": "Bilmiş Bediş",
    "VN (vietnam)": "Lily Lí Lắc"
  },
  {
    "Character Name (EN)": "Doctor Worry",
    "EN": "Doctor Worry",
    "AR": "الدكتور نجيب",
    "CN_TR": "糊塗博士",
    "CZ (cestina)": "Doktor Lek",
    "FR": "Docteur Névrose",
    "DE": "Dr. Kummer",
    "HU (magyar)": "dr. Nyápic",
    "ID": "Dr. Jeri",
    "IT": "Dottor Preoccupazione",
    "JP": "ドクター心配性",
    "KR": "걱정 박사",
    "MY": "Doktor Ghisau",
    "PL (Polski)": "Doktor Zmartwiak",
    "PT": "Doutor Preocupas",
    "RO": "Doctor Bizaro",
    "RU": "Тревожный док",
    "ES": "Doctor Preocupón",
    "TH (Thai)": "ด็อกเตอร์อัจ",
    "TR": "Doktor Civan",
    "VN (vietnam)": "Bác Sĩ Lo Âu"
  }
        }
        
        # Create response with the JSON file
        response = make_response(json.dumps(example_data, ensure_ascii=False, indent=4))
        response.headers["Content-Type"] = "application/json"
        response.headers["Content-Disposition"] = "attachment; filename=example_chars.json"
        
        return response

if __name__ == '__main__':
    socketio.run(app, debug=True, host='127.0.0.1', port=5001, allow_unsafe_werkzeug=True)

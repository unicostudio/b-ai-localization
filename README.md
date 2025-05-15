# AI-Powered Game Localization Tool

A web-based tool for extracting text from game images using OCR, generating image descriptions with vision models, and automatically localizing content to multiple languages using large language models.

## Features

- **OCR Integration**: Extract text from game screenshots using Pytesseract
- **AI Vision Analysis**: Generate descriptions of game images using OpenRouter's vision models
- **Multi-language Support**: Generate localizations in Turkish, French, German, and other languages
- **Web Interface**: User-friendly interface for uploading files and configuring the localization process
- **Real-time Progress**: Socket.IO based progress updates during processing
- **Multiple Export Formats**: Export to JSON (complete output or language-specific files)

## Requirements

- Python 3.8+
- Flask
- OpenRouter API key (for AI models)
- Pytesseract (for OCR)

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/unicostudio/b-ai-localization.git
   cd b-ai-localization
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root and add your OpenRouter API key:
   ```bash
   OPENROUTER_API_KEY=your_api_key_here
   ```

## Usage

1. Start the application:
   ```bash
   python app.py
   ```

2. Open your browser and navigate to `http://127.0.0.1:5001`

3. Upload a CSV file with the following columns:
   - `IDS`: Identifier for the game image
   - `EN`: English text to be localized
   - `LOCID`: Localization ID or context

4. Select the images directory containing game screenshots
   - Image filenames should contain the ID from the CSV file (e.g., "ID1.png")

5. Choose target languages and AI model

6. Start the localization process

7. Download the generated files when processing completes

## Input Format

### CSV format
```
IDS;EN;LOCID
ID1;Tap on the biggest flower.;LEVEL_TEXT_1
ID1;Drag out the Sun behind Lily's head.;HINT_1_1
ID2;Lets find Tricky Lily;LEVEL_TEXT_2
```

## Models Supported

- Grok 3 (x-ai/grok-3-beta)
- GPT-4.1 (openai/gpt-4.1)
- Claude 3.7 Sonnet (anthropic/claude-3.7-sonnet)
- Gemini Flash (google/gemini-flash-1.5-8b)

## License

MIT License

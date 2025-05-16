#!/usr/bin/env python
# Test script to verify the JSON output format from the minimal_localization_tool

from minimal_localization_tool import process_localization, replace_character_names
import json
import re

# Sample input
description = "A puzzle screen showing a cartoon character with flowers"
sample_char_data = char_example.json

# Test 1: Basic text
english_text = "Tap on the biggest flower."
result = process_localization(
    description=description,
    english_text=english_text,
    model="grok3",
    languages=["TR"],
    debug=True,
    char_lookup=sample_char_data
)

print("Test 1: Basic text")
print(json.dumps(result, indent=2, ensure_ascii=False))

# Test 2: Text with character name
english_text_with_name = "Drag out the Sun behind Lilly's head."
result2 = process_localization(
    description=description,
    english_text=english_text_with_name,
    model="grok3",
    languages=["TR"],
    debug=True,
    char_lookup=sample_char_data
)

print("\nTest 2: Text with character name")
print(json.dumps(result2, indent=2, ensure_ascii=False))

# Test 3: Simulate text with **Text:** prefix
formatted_text = "**Text:** Güneş nerede?"

# Test our cleanup function directly
def clean_text(text):
    # Remove **Text:** prefix if present
    if "**Text:**" in text:
        text = re.sub(r'\*\*Text:\*\*\s*', '', text)
        
    # Remove any explanation sections
    for pattern in [r'\*\*Explanation:\*\*.*', r'\n\n\*\*Explanation:.*', r'\*\*Localization Notes:\*\*.*']:
        text = re.sub(pattern, '', text, flags=re.DOTALL)
        
    # Final cleanup
    text = text.strip()
    return text

print("\nTest 3: Text with **Text:** prefix")
print(f"Original: {formatted_text}")
print(f"Cleaned: {clean_text(formatted_text)}")

# Test 4: Text with explanation
formatted_text_with_explanation = "**Text:** Güneş nerede?\n\n**Explanation:** This is the Turkish translation for 'Where is the sun?'"
print("\nTest 4: Text with explanation")
print(f"Original: {formatted_text_with_explanation}")
print(f"Cleaned: {clean_text(formatted_text_with_explanation)}")

# Test 5: Complex formatting from the example
complex_text = "**Text:** Marslı burada\n\n**Explanation:** The translation 'Marslı burada' directly translates to 'The Martian is here' in Turkish, maintaining the original meaning and simplicity of the hint. This phrasing uses 'Marslı' as the culturally appropriate term for 'Martian' and 'burada' for 'is here', resulting in a natural-sounding hint in Turkish that clearly guides the player to identify or interact with a Martian character in the game. The translation preserves the brevity and directness of the original hint, making it easy for children to understand without adding unnecessary complexity."
print("\nTest 5: Complex formatting from user example")
print(f"Cleaned: {clean_text(complex_text)}")

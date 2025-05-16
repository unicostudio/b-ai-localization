#!/usr/bin/env python
# Test script to verify that character replacements are working with example_chars.json

from minimal_localization_tool import load_character_data, replace_character_names, process_localization
import json
import os
import re

# Path to the example characters file
example_chars_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'example_chars.json')

# Load the character data from example_chars.json
print(f"Testing character replacements using file: {example_chars_file}")
char_lookup = load_character_data(example_chars_file)

# Print available character mappings
print("\nAvailable character mappings:")
for lang, chars in char_lookup.items():
    print(f"{lang}: {list(chars.keys())}")

# Test sentences with different character names
test_sentences = [
    "Lily is playing with the flowers.",
    "Lilly is playing with the flowers.",  # Misspelling
    "Granny Amy needs help with her cookies.",
    "Uncle Bubba is hiding something.",
    "Dr. Worry is always worried.",
    "Larry wants to marry me.",
    "Lary not merry me."  # Misspelling
]

print("\n=== Testing Character Replacements ===")
for sentence in test_sentences:
    # Test Turkish replacements
    tr_result = replace_character_names(sentence, "turkish", char_lookup)
    print(f"\nEN: {sentence}")
    print(f"TR: {tr_result}")

print("\n=== Testing Full Localization Process ===")
# Test the full localization process with character replacements
image_description = "A cartoon scene with characters Lily and Uncle Bubba"
english_text = "Help Lily find Uncle Bubba's hidden treasure."

# Process with debug mode to avoid API calls
result = process_localization(
    description=image_description,
    english_text=english_text,
    model="grok3",
    languages=["TR"],
    debug=True,
    char_lookup=char_lookup
)

print("\nFull localization result with character replacements:")
print(json.dumps(result, indent=2, ensure_ascii=False))

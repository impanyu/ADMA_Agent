import json

def is_json(myjson):
    if myjson.startswith("```json") and myjson.endswith("```"):
        # Strip the first line (```json\n) and the last line (```)
        myjson = myjson.split('\n', 1)[1].rsplit('\n', 1)[0]
    try:
        result = json.loads(myjson)
    except ValueError as e:
        return False
    return result

import re


def extract_json(text):
    """
    Extracts the first valid JSON string from a given text.

    Args:
    text (str): The input text containing a JSON string.

    Returns:
    dict: The first valid JSON object found, or None if no valid JSON is found.
    """
    # Regex pattern to find JSON objects
    pattern = r'\{(?:[^{}]|(?R))*\}'
    matches = re.findall(pattern, text, re.DOTALL)

    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue  # If it's not a valid JSON, continue with the next match

    return None  # Return None if no valid JSON objects are found

def find_largest_enclosed_json(text):
    """
    Finds the largest substring enclosed in '{}' including nested structures.

    Args:
    text (str): The input text containing one or more potentially nested '{}' substrates.

    Returns:
    str: The largest valid enclosed substring found, or None if no valid enclosure is found.
    """
    max_length = 0
    max_substring = None
    stack = []
    start_index = {}

    for i, char in enumerate(text):
        if char == '{':
            stack.append(i)
            start_index[len(stack)] = i  # Remember the start index for this level of depth
        elif char == '}' and stack:
            start = stack.pop()  # Pop the last unmatched '{'
            current_length = i - start + 1
            if current_length > max_length:
                max_length = current_length
                max_substring = text[start:i+1]

    return max_substring
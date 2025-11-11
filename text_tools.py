"""
Text Tools Module for AIezzy
Provides text manipulation and generation utilities

Functions:
- word_counter: Count words, characters, sentences, paragraphs, reading time
- case_converter: Convert text case (UPPER, lower, Title, Sentence, etc.)
- text_formatter: Clean and format text (remove extra spaces, line breaks)
- lorem_ipsum_generator: Generate placeholder Lorem Ipsum text
- find_and_replace: Find and replace text in bulk
- password_generator: Generate secure random passwords

Created: October 2025
"""

import re
import random
import string
from typing import Dict, Tuple


def word_counter(text: str) -> Dict[str, int]:
    """
    Count words, characters, sentences, paragraphs, and estimate reading time.

    Args:
        text: Input text to analyze

    Returns:
        Dictionary containing:
        - words: Number of words
        - characters: Number of characters (with spaces)
        - characters_no_spaces: Number of characters (without spaces)
        - sentences: Number of sentences
        - paragraphs: Number of paragraphs
        - reading_time_minutes: Estimated reading time (avg 200 words/min)
    """
    if not text or not text.strip():
        return {
            'words': 0,
            'characters': 0,
            'characters_no_spaces': 0,
            'sentences': 0,
            'paragraphs': 0,
            'reading_time_minutes': 0
        }

    # Count words (split by whitespace)
    words = len(text.split())

    # Count characters
    characters = len(text)
    characters_no_spaces = len(text.replace(' ', '').replace('\n', '').replace('\t', ''))

    # Count sentences (end with . ! ? followed by space or end of string)
    sentence_pattern = r'[.!?]+(?:\s|$)'
    sentences = len(re.findall(sentence_pattern, text))
    if sentences == 0 and words > 0:
        sentences = 1  # At least one sentence if there's text

    # Count paragraphs (separated by blank lines or \n\n)
    paragraphs = len([p for p in re.split(r'\n\s*\n', text.strip()) if p.strip()])
    if paragraphs == 0 and words > 0:
        paragraphs = 1  # At least one paragraph if there's text

    # Estimate reading time (average 200 words per minute)
    reading_time_minutes = round(words / 200, 1) if words > 0 else 0

    return {
        'words': words,
        'characters': characters,
        'characters_no_spaces': characters_no_spaces,
        'sentences': sentences,
        'paragraphs': paragraphs,
        'reading_time_minutes': reading_time_minutes
    }


def case_converter(text: str, case_type: str) -> str:
    """
    Convert text to different cases.

    Args:
        text: Input text to convert
        case_type: Type of case conversion
            - 'upper': UPPERCASE
            - 'lower': lowercase
            - 'title': Title Case
            - 'sentence': Sentence case
            - 'alternating': aLtErNaTiNg CaSe
            - 'inverse': iNVERSE cASE

    Returns:
        Converted text
    """
    if not text:
        return text

    case_type = case_type.lower()

    if case_type == 'upper':
        return text.upper()

    elif case_type == 'lower':
        return text.lower()

    elif case_type == 'title':
        return text.title()

    elif case_type == 'sentence':
        # Capitalize first letter of each sentence
        sentences = re.split(r'([.!?]+\s+)', text)
        result = []
        for i, part in enumerate(sentences):
            if i % 2 == 0:  # Actual sentence text
                if part:
                    result.append(part[0].upper() + part[1:].lower() if len(part) > 0 else '')
            else:  # Punctuation
                result.append(part)
        return ''.join(result)

    elif case_type == 'alternating':
        # aLtErNaTiNg CaSe
        result = []
        is_upper = False
        for char in text:
            if char.isalpha():
                result.append(char.upper() if is_upper else char.lower())
                is_upper = not is_upper
            else:
                result.append(char)
        return ''.join(result)

    elif case_type == 'inverse':
        # Swap case: uppercase → lowercase, lowercase → uppercase
        return text.swapcase()

    else:
        raise ValueError(f"Unknown case type: {case_type}")


def text_formatter(text: str,
                   remove_extra_spaces: bool = True,
                   remove_extra_line_breaks: bool = True,
                   trim_lines: bool = True) -> str:
    """
    Clean and format text by removing extra spaces and line breaks.

    Args:
        text: Input text to format
        remove_extra_spaces: Remove multiple consecutive spaces
        remove_extra_line_breaks: Remove multiple consecutive line breaks
        trim_lines: Trim whitespace from start/end of each line

    Returns:
        Formatted text
    """
    if not text:
        return text

    result = text

    # Remove extra spaces (multiple spaces → single space)
    if remove_extra_spaces:
        result = re.sub(r' +', ' ', result)

    # Trim whitespace from each line
    if trim_lines:
        lines = result.split('\n')
        lines = [line.strip() for line in lines]
        result = '\n'.join(lines)

    # Remove extra line breaks (multiple \n → single \n)
    if remove_extra_line_breaks:
        result = re.sub(r'\n\s*\n+', '\n\n', result)

    # Trim leading/trailing whitespace
    result = result.strip()

    return result


# Lorem Ipsum source text
LOREM_IPSUM_WORDS = [
    "lorem", "ipsum", "dolor", "sit", "amet", "consectetur", "adipiscing", "elit",
    "sed", "do", "eiusmod", "tempor", "incididunt", "ut", "labore", "et", "dolore",
    "magna", "aliqua", "enim", "ad", "minim", "veniam", "quis", "nostrud",
    "exercitation", "ullamco", "laboris", "nisi", "aliquip", "ex", "ea", "commodo",
    "consequat", "duis", "aute", "irure", "in", "reprehenderit", "voluptate",
    "velit", "esse", "cillum", "fugiat", "nulla", "pariatur", "excepteur", "sint",
    "occaecat", "cupidatat", "non", "proident", "sunt", "culpa", "qui", "officia",
    "deserunt", "mollit", "anim", "id", "est", "laborum"
]


def lorem_ipsum_generator(count: int = 5, unit: str = 'paragraphs') -> str:
    """
    Generate Lorem Ipsum placeholder text.

    Args:
        count: Number of units to generate
        unit: Type of unit ('paragraphs', 'sentences', 'words')

    Returns:
        Generated Lorem Ipsum text
    """
    if count <= 0:
        return ""

    unit = unit.lower()

    if unit == 'words':
        # Generate specified number of words
        words = []
        for i in range(count):
            words.append(LOREM_IPSUM_WORDS[i % len(LOREM_IPSUM_WORDS)])
        result = ' '.join(words)
        return result.capitalize() + '.'

    elif unit == 'sentences':
        # Generate specified number of sentences
        sentences = []
        for _ in range(count):
            sentence_length = random.randint(8, 16)
            words = []
            for i in range(sentence_length):
                words.append(random.choice(LOREM_IPSUM_WORDS))
            sentence = ' '.join(words)
            sentences.append(sentence.capitalize() + '.')
        return ' '.join(sentences)

    elif unit == 'paragraphs':
        # Generate specified number of paragraphs
        paragraphs = []
        for _ in range(count):
            paragraph_sentences = random.randint(4, 7)
            sentences = []
            for _ in range(paragraph_sentences):
                sentence_length = random.randint(8, 16)
                words = []
                for i in range(sentence_length):
                    words.append(random.choice(LOREM_IPSUM_WORDS))
                sentence = ' '.join(words)
                sentences.append(sentence.capitalize() + '.')
            paragraphs.append(' '.join(sentences))
        return '\n\n'.join(paragraphs)

    else:
        raise ValueError(f"Unknown unit type: {unit}. Use 'paragraphs', 'sentences', or 'words'.")


def find_and_replace(text: str,
                     find: str,
                     replace: str,
                     case_sensitive: bool = True,
                     whole_word: bool = False) -> Tuple[str, int]:
    """
    Find and replace text in bulk.

    Args:
        text: Input text
        find: Text to find
        replace: Text to replace with
        case_sensitive: Whether search is case sensitive
        whole_word: Whether to match whole words only

    Returns:
        Tuple of (result_text, replacement_count)
    """
    if not text or not find:
        return text, 0

    # Build regex pattern
    pattern = re.escape(find)

    if whole_word:
        pattern = r'\b' + pattern + r'\b'

    flags = 0 if case_sensitive else re.IGNORECASE

    # Count replacements
    count = len(re.findall(pattern, text, flags=flags))

    # Perform replacement
    result = re.sub(pattern, replace, text, flags=flags)

    return result, count


def password_generator(length: int = 16,
                      include_uppercase: bool = True,
                      include_lowercase: bool = True,
                      include_numbers: bool = True,
                      include_symbols: bool = True,
                      exclude_ambiguous: bool = True) -> str:
    """
    Generate a secure random password.

    Args:
        length: Password length (minimum 4)
        include_uppercase: Include uppercase letters (A-Z)
        include_lowercase: Include lowercase letters (a-z)
        include_numbers: Include numbers (0-9)
        include_symbols: Include symbols (!@#$%^&*...)
        exclude_ambiguous: Exclude ambiguous characters (l, 1, I, O, 0)

    Returns:
        Generated password string
    """
    if length < 4:
        length = 4  # Minimum length for security

    # Define character sets
    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    numbers = string.digits
    symbols = "!@#$%^&*()-_=+[]{}|;:,.<>?/"

    # Remove ambiguous characters if requested
    if exclude_ambiguous:
        uppercase = uppercase.replace('I', '').replace('O', '')
        lowercase = lowercase.replace('l', '').replace('o', '')
        numbers = numbers.replace('0', '').replace('1', '')
        symbols = symbols.replace('|', '')

    # Build character pool
    char_pool = ""
    required_chars = []

    if include_uppercase:
        char_pool += uppercase
        required_chars.append(random.choice(uppercase))

    if include_lowercase:
        char_pool += lowercase
        required_chars.append(random.choice(lowercase))

    if include_numbers:
        char_pool += numbers
        required_chars.append(random.choice(numbers))

    if include_symbols:
        char_pool += symbols
        required_chars.append(random.choice(symbols))

    if not char_pool:
        # Default to alphanumeric if nothing selected
        char_pool = string.ascii_letters + string.digits
        required_chars = [random.choice(string.ascii_letters), random.choice(string.digits)]

    # Generate password ensuring at least one character from each selected category
    remaining_length = length - len(required_chars)
    if remaining_length < 0:
        remaining_length = 0

    password_chars = required_chars + [random.choice(char_pool) for _ in range(remaining_length)]

    # Shuffle to avoid predictable patterns
    random.shuffle(password_chars)

    return ''.join(password_chars)


# Test functions
if __name__ == "__main__":
    # Test word counter
    test_text = "Hello world! This is a test. How are you?\n\nThis is a new paragraph."
    stats = word_counter(test_text)
    print("Word Counter:", stats)

    # Test case converter
    print("\nCase Converter:")
    print("UPPER:", case_converter("Hello World", "upper"))
    print("lower:", case_converter("Hello World", "lower"))
    print("Title:", case_converter("hello world", "title"))
    print("Sentence:", case_converter("hello world. how are you?", "sentence"))
    print("aLtErNaTiNg:", case_converter("hello world", "alternating"))
    print("iNVERSE:", case_converter("Hello World", "inverse"))

    # Test text formatter
    messy_text = "  Hello    world  \n\n\n  How   are   you?  \n\n  "
    print("\nText Formatter:")
    print("Original:", repr(messy_text))
    print("Formatted:", repr(text_formatter(messy_text)))

    # Test lorem ipsum
    print("\nLorem Ipsum (3 paragraphs):")
    print(lorem_ipsum_generator(3, 'paragraphs')[:100] + "...")

    # Test find and replace
    test_text = "The quick brown fox jumps over the lazy dog. The fox is quick."
    result, count = find_and_replace(test_text, "fox", "cat", case_sensitive=True)
    print(f"\nFind and Replace: '{test_text}' -> '{result}' ({count} replacements)")

    # Test password generator
    print("\nPassword Generator:")
    print("Default:", password_generator())
    print("16 chars:", password_generator(16))
    print("No symbols:", password_generator(16, include_symbols=False))
    print("Only lowercase + numbers:", password_generator(12, include_uppercase=False, include_symbols=False))

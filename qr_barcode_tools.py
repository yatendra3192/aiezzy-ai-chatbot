"""
QR Code and Barcode Tools Module for AIezzy
Generate QR codes and barcodes

Functions:
- generate_qr_code: Create QR codes for text, URLs, WiFi, vCards
- generate_barcode: Create barcodes (EAN, UPC, Code128, Code39, etc.)

Dependencies:
- qrcode: QR code generation
- python-barcode: Barcode generation
- Pillow: Image processing

Created: October 2025
"""

import os
import io
import qrcode
from qrcode.image.pil import PilImage
import barcode
from barcode.writer import ImageWriter
from PIL import Image


def generate_qr_code(data: str,
                     output_path: str = None,
                     size: int = 10,
                     border: int = 2,
                     error_correction: str = 'M',
                     fill_color: str = 'black',
                     back_color: str = 'white') -> str:
    """
    Generate a QR code image.

    Args:
        data: Data to encode (text, URL, etc.)
        output_path: Path to save QR code image (PNG). If None, auto-generate in assets/
        size: Size of QR code (1-40, default 10)
        border: Border size in boxes (default 2, minimum 1)
        error_correction: Error correction level ('L', 'M', 'Q', 'H')
            - L: ~7% correction
            - M: ~15% correction (default)
            - Q: ~25% correction
            - H: ~30% correction
        fill_color: QR code color (default 'black')
        back_color: Background color (default 'white')

    Returns:
        Path to generated QR code image

    Example:
        # Generate QR code for URL
        path = generate_qr_code("https://aiezzy.com")

        # Generate WiFi QR code
        wifi_data = "WIFI:T:WPA;S:MyNetwork;P:password123;;"
        path = generate_qr_code(wifi_data)

        # Generate vCard QR code
        vcard = "BEGIN:VCARD\\nVERSION:3.0\\nFN:John Doe\\nTEL:+1234567890\\nEND:VCARD"
        path = generate_qr_code(vcard)
    """
    if not data:
        raise ValueError("Data cannot be empty")

    # Validate size
    if size < 1:
        size = 1
    elif size > 40:
        size = 40

    # Validate border
    if border < 1:
        border = 1

    # Map error correction string to constant
    error_correction_map = {
        'L': qrcode.constants.ERROR_CORRECT_L,
        'M': qrcode.constants.ERROR_CORRECT_M,
        'Q': qrcode.constants.ERROR_CORRECT_Q,
        'H': qrcode.constants.ERROR_CORRECT_H
    }
    ec_level = error_correction_map.get(error_correction.upper(), qrcode.constants.ERROR_CORRECT_M)

    # Create QR code
    qr = qrcode.QRCode(
        version=None,  # Auto-determine version based on data
        error_correction=ec_level,
        box_size=size,
        border=border,
    )

    qr.add_data(data)
    qr.make(fit=True)

    # Generate image
    img = qr.make_image(fill_color=fill_color, back_color=back_color)

    # Generate output path if not provided
    if not output_path:
        timestamp = int(__import__('time').time())
        os.makedirs('assets', exist_ok=True)
        output_path = f"assets/qr_{timestamp}.png"

    # Save QR code
    img.save(output_path)

    print(f"INFO: QR code generated successfully: {output_path}")
    return output_path


def generate_wifi_qr(ssid: str,
                     password: str = None,
                     security: str = 'WPA',
                     hidden: bool = False,
                     output_path: str = None) -> str:
    """
    Generate a WiFi QR code for easy network connection.

    Args:
        ssid: WiFi network name
        password: WiFi password (optional for open networks)
        security: Security type ('WPA', 'WEP', 'nopass')
        hidden: Whether network is hidden
        output_path: Path to save QR code

    Returns:
        Path to generated QR code image
    """
    # Build WiFi string format: WIFI:T:WPA;S:MyNetwork;P:password;;
    wifi_parts = [f"WIFI:T:{security};S:{ssid}"]

    if password:
        wifi_parts.append(f"P:{password}")

    if hidden:
        wifi_parts.append("H:true")

    wifi_data = ';'.join(wifi_parts) + ";;"

    return generate_qr_code(wifi_data, output_path=output_path)


def generate_vcard_qr(name: str,
                      phone: str = None,
                      email: str = None,
                      organization: str = None,
                      website: str = None,
                      output_path: str = None) -> str:
    """
    Generate a vCard QR code for contact information.

    Args:
        name: Full name
        phone: Phone number
        email: Email address
        organization: Organization/company name
        website: Website URL
        output_path: Path to save QR code

    Returns:
        Path to generated QR code image
    """
    # Build vCard format
    vcard_parts = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"FN:{name}"
    ]

    if phone:
        vcard_parts.append(f"TEL:{phone}")

    if email:
        vcard_parts.append(f"EMAIL:{email}")

    if organization:
        vcard_parts.append(f"ORG:{organization}")

    if website:
        vcard_parts.append(f"URL:{website}")

    vcard_parts.append("END:VCARD")

    vcard_data = "\\n".join(vcard_parts)

    return generate_qr_code(vcard_data, output_path=output_path)


def generate_barcode(data: str,
                     barcode_type: str = 'code128',
                     output_path: str = None,
                     add_text: bool = True) -> str:
    """
    Generate a barcode image.

    Args:
        data: Data to encode
        barcode_type: Type of barcode
            - 'code128': Code 128 (default, alphanumeric)
            - 'code39': Code 39 (alphanumeric)
            - 'ean13': EAN-13 (13 digits, retail products)
            - 'ean8': EAN-8 (8 digits)
            - 'upca': UPC-A (12 digits, US/Canada retail)
            - 'isbn13': ISBN-13 (books)
            - 'isbn10': ISBN-10 (books)
            - 'issn': ISSN (periodicals)
        output_path: Path to save barcode image (PNG)
        add_text: Whether to add text below barcode

    Returns:
        Path to generated barcode image
    """
    if not data:
        raise ValueError("Data cannot be empty")

    # Map barcode type to python-barcode class
    barcode_types = {
        'code128': 'code128',
        'code39': 'code39',
        'ean13': 'ean13',
        'ean8': 'ean8',
        'ean': 'ean13',
        'upca': 'upca',
        'upc': 'upca',
        'isbn13': 'isbn13',
        'isbn10': 'isbn10',
        'isbn': 'isbn13',
        'issn': 'issn'
    }

    barcode_class_name = barcode_types.get(barcode_type.lower())
    if not barcode_class_name:
        raise ValueError(f"Unknown barcode type: {barcode_type}. Supported types: {list(barcode_types.keys())}")

    # Get barcode class
    try:
        barcode_class = barcode.get_barcode_class(barcode_class_name)
    except Exception as e:
        raise ValueError(f"Error getting barcode class '{barcode_class_name}': {str(e)}")

    # Validate data format for specific barcode types
    if barcode_class_name in ['ean13', 'ean8', 'upca', 'isbn13', 'isbn10']:
        # These require numeric data
        if not data.replace('-', '').isdigit():
            raise ValueError(f"{barcode_type} requires numeric data only")

    # Generate output path if not provided
    if not output_path:
        timestamp = int(__import__('time').time())
        os.makedirs('assets', exist_ok=True)
        output_path = f"assets/barcode_{timestamp}"  # Extension added by library

    # Generate barcode
    try:
        # Create barcode instance
        barcode_instance = barcode_class(data, writer=ImageWriter())

        # Save barcode (library adds .png extension automatically)
        options = {
            'write_text': add_text,
            'module_width': 0.3,
            'module_height': 15.0,
            'font_size': 10,
            'text_distance': 5.0,
            'quiet_zone': 6.5
        }

        full_path = barcode_instance.save(output_path, options=options)

        print(f"INFO: Barcode generated successfully: {full_path}")
        return full_path

    except Exception as e:
        raise Exception(f"Error generating barcode: {str(e)}")


# Test functions
if __name__ == "__main__":
    print("Testing QR Code and Barcode Tools...\n")

    # Test QR code generation
    print("1. Testing QR code for URL...")
    qr_path = generate_qr_code("https://aiezzy.com", output_path="assets/test_qr_url.png")
    print(f"   Generated: {qr_path}\n")

    # Test WiFi QR code
    print("2. Testing WiFi QR code...")
    wifi_qr = generate_wifi_qr("MyNetwork", "password123", security="WPA")
    print(f"   Generated: {wifi_qr}\n")

    # Test vCard QR code
    print("3. Testing vCard QR code...")
    vcard_qr = generate_vcard_qr(
        name="John Doe",
        phone="+1234567890",
        email="john@example.com",
        organization="AIezzy",
        website="https://aiezzy.com"
    )
    print(f"   Generated: {vcard_qr}\n")

    # Test barcode generation
    print("4. Testing Code128 barcode...")
    barcode_path = generate_barcode("AIEZZY2025", barcode_type="code128", output_path="assets/test_barcode")
    print(f"   Generated: {barcode_path}\n")

    # Test EAN-13 barcode
    print("5. Testing EAN-13 barcode...")
    try:
        ean_path = generate_barcode("1234567890123", barcode_type="ean13", output_path="assets/test_ean13")
        print(f"   Generated: {ean_path}\n")
    except Exception as e:
        print(f"   Error: {e}\n")

    print("All tests completed!")

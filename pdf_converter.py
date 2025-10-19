"""
PDF Conversion & Processing Module
Provides tools for converting between PDF and various formats
"""

import os
import io
import pathlib
from typing import List, Tuple
from PIL import Image
import fitz  # PyMuPDF
import pypdf
import img2pdf
from pdf2image import convert_from_path
from docx import Document
from openpyxl import Workbook, load_workbook
from pptx import Presentation
from pptx.util import Inches

# Setup directories
DATA_DIR = os.getenv('RAILWAY_VOLUME_MOUNT_PATH', os.path.dirname(os.path.abspath(__file__)))
DOCUMENTS_DIR = os.path.join(DATA_DIR, 'documents')
ASSETS_DIR = os.path.join(DATA_DIR, 'assets')

# Ensure directories exist
os.makedirs(DOCUMENTS_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)


# ==================== PDF to Images ====================

def pdf_to_images(pdf_path: str, output_format: str = 'png', dpi: int = 200) -> List[str]:
    """
    Convert PDF pages to individual image files

    Args:
        pdf_path: Path to PDF file
        output_format: 'png' or 'jpg'
        dpi: Image resolution (default 200)

    Returns:
        List of paths to generated image files
    """
    try:
        # Convert PDF to images
        images = convert_from_path(pdf_path, dpi=dpi)

        output_paths = []
        pdf_name = pathlib.Path(pdf_path).stem

        for i, image in enumerate(images):
            output_filename = f"{pdf_name}_page_{i+1}.{output_format}"
            output_path = os.path.join(ASSETS_DIR, output_filename)

            # Save image
            image.save(output_path, format=output_format.upper())
            output_paths.append(output_path)

        return output_paths

    except Exception as e:
        raise Exception(f"Failed to convert PDF to images: {str(e)}")


# ==================== Images to PDF ====================

def images_to_pdf(image_paths: List[str], output_name: str = None) -> str:
    """
    Convert multiple images into a single PDF

    Args:
        image_paths: List of image file paths
        output_name: Optional output filename

    Returns:
        Path to generated PDF file
    """
    try:
        if not output_name:
            output_name = f"combined_images_{int(time.time())}.pdf"

        if not output_name.endswith('.pdf'):
            output_name += '.pdf'

        output_path = os.path.join(DOCUMENTS_DIR, output_name)

        # Validate that all image files exist
        for img_path in image_paths:
            if not os.path.exists(img_path):
                raise Exception(f"Image file not found: {img_path}")

        # Try using img2pdf first (faster, better quality)
        # img2pdf can accept file paths directly when passed as a list
        try:
            with open(output_path, "wb") as f:
                # Pass image paths as a list - img2pdf will handle them correctly
                f.write(img2pdf.convert(image_paths))
            print(f"Successfully converted {len(image_paths)} images to PDF using img2pdf")
            return output_path
        except Exception as img2pdf_error:
            print(f"img2pdf failed: {img2pdf_error}, trying PIL fallback...")

            # Fallback: Use PIL to convert images to RGB and then to PDF
            images = []
            for i, img_path in enumerate(image_paths):
                print(f"Processing image {i+1}/{len(image_paths)}: {img_path}")
                try:
                    img = Image.open(img_path)
                    print(f"  Original mode: {img.mode}, size: {img.size}")
                    # Convert to RGB if necessary (handles RGBA, P, etc.)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                        print(f"  Converted to RGB")
                    images.append(img)
                except Exception as img_error:
                    print(f"  ERROR processing image: {img_error}")
                    # Continue with other images
                    continue

            # Save as PDF
            if images:
                print(f"Saving {len(images)} images to PDF: {output_path}")
                images[0].save(output_path, save_all=True, append_images=images[1:] if len(images) > 1 else [], format='PDF')
                return output_path
            else:
                raise Exception("No valid images to convert")

    except Exception as e:
        raise Exception(f"Failed to convert images to PDF: {str(e)}")


# ==================== PDF to Word ====================

def pdf_to_word(pdf_path: str, output_name: str = None) -> str:
    """
    Convert PDF to Word document (DOCX)
    Extracts text and attempts to preserve basic formatting

    Args:
        pdf_path: Path to PDF file
        output_name: Optional output filename

    Returns:
        Path to generated Word file
    """
    try:
        # Open PDF
        doc_pdf = fitz.open(pdf_path)

        # Create Word document
        doc_word = Document()

        # Extract text from each page
        for page_num in range(len(doc_pdf)):
            page = doc_pdf[page_num]
            text = page.get_text()

            # Add page heading
            if page_num > 0:
                doc_word.add_page_break()

            # Add text content
            doc_word.add_paragraph(text)

        # Generate output path
        if not output_name:
            pdf_name = pathlib.Path(pdf_path).stem
            output_name = f"{pdf_name}_converted.docx"

        if not output_name.endswith('.docx'):
            output_name += '.docx'

        output_path = os.path.join(DOCUMENTS_DIR, output_name)
        doc_word.save(output_path)

        doc_pdf.close()
        return output_path

    except Exception as e:
        raise Exception(f"Failed to convert PDF to Word: {str(e)}")


# ==================== PDF to Excel ====================

def pdf_to_excel(pdf_path: str, output_name: str = None) -> str:
    """
    Convert PDF to Excel spreadsheet (XLSX)
    Extracts tables and text data

    Args:
        pdf_path: Path to PDF file
        output_name: Optional output filename

    Returns:
        Path to generated Excel file
    """
    try:
        # Open PDF
        doc = fitz.open(pdf_path)

        # Create Excel workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Extracted Data"

        # Extract text from each page
        current_row = 1
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()

            # Add page header
            ws.cell(row=current_row, column=1, value=f"Page {page_num + 1}")
            current_row += 1

            # Split text into lines and add to cells
            lines = text.split('\n')
            for line in lines:
                if line.strip():
                    ws.cell(row=current_row, column=1, value=line)
                    current_row += 1

            current_row += 1  # Add space between pages

        # Generate output path
        if not output_name:
            pdf_name = pathlib.Path(pdf_path).stem
            output_name = f"{pdf_name}_converted.xlsx"

        if not output_name.endswith('.xlsx'):
            output_name += '.xlsx'

        output_path = os.path.join(DOCUMENTS_DIR, output_name)
        wb.save(output_path)

        doc.close()
        return output_path

    except Exception as e:
        raise Exception(f"Failed to convert PDF to Excel: {str(e)}")


# ==================== PDF to PowerPoint ====================

def pdf_to_powerpoint(pdf_path: str, output_name: str = None, slides_per_page: bool = True) -> str:
    """
    Convert PDF to PowerPoint presentation (PPTX)
    Each page becomes a slide with image or text

    Args:
        pdf_path: Path to PDF file
        output_name: Optional output filename
        slides_per_page: If True, each PDF page becomes one slide

    Returns:
        Path to generated PowerPoint file
    """
    try:
        # Open PDF
        doc = fitz.open(pdf_path)

        # Create PowerPoint presentation
        prs = Presentation()
        prs.slide_width = Inches(10)
        prs.slide_height = Inches(7.5)

        # Process each page
        for page_num in range(len(doc)):
            page = doc[page_num]

            # Add blank slide
            blank_slide_layout = prs.slide_layouts[6]  # Blank layout
            slide = prs.slides.add_slide(blank_slide_layout)

            # Convert page to image
            pix = page.get_pixmap(dpi=150)
            img_data = pix.tobytes("png")

            # Save temp image
            temp_img_path = os.path.join(ASSETS_DIR, f"temp_slide_{page_num}.png")
            pix.save(temp_img_path)

            # Add image to slide
            left = Inches(0.5)
            top = Inches(0.5)
            width = Inches(9)
            slide.shapes.add_picture(temp_img_path, left, top, width=width)

            # Clean up temp file
            try:
                os.remove(temp_img_path)
            except:
                pass

        # Generate output path
        if not output_name:
            pdf_name = pathlib.Path(pdf_path).stem
            output_name = f"{pdf_name}_converted.pptx"

        if not output_name.endswith('.pptx'):
            output_name += '.pptx'

        output_path = os.path.join(DOCUMENTS_DIR, output_name)
        prs.save(output_path)

        doc.close()
        return output_path

    except Exception as e:
        raise Exception(f"Failed to convert PDF to PowerPoint: {str(e)}")


# ==================== Word to PDF ====================

def word_to_pdf(docx_path: str, output_name: str = None) -> str:
    """
    Convert Word document to PDF using LibreOffice

    Args:
        docx_path: Path to Word file
        output_name: Optional output filename

    Returns:
        Path to generated PDF file
    """
    try:
        import subprocess

        # Validate file exists
        if not os.path.exists(docx_path):
            raise Exception(f"Word file not found: {docx_path}")

        # Generate output name
        if not output_name:
            docx_name = pathlib.Path(docx_path).stem
            output_name = f"{docx_name}_converted.pdf"

        if not output_name.endswith('.pdf'):
            output_name += '.pdf'

        output_path = os.path.join(DOCUMENTS_DIR, output_name)

        # Use LibreOffice to convert to PDF
        # --headless: run without GUI
        # --convert-to pdf: output format
        # --outdir: output directory
        subprocess.run([
            'libreoffice',
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', DOCUMENTS_DIR,
            docx_path
        ], check=True, capture_output=True, timeout=60)

        # LibreOffice creates the file with original name + .pdf extension
        # Rename if needed
        temp_output = os.path.join(DOCUMENTS_DIR, pathlib.Path(docx_path).stem + '.pdf')
        if temp_output != output_path and os.path.exists(temp_output):
            os.rename(temp_output, output_path)

        return output_path

    except subprocess.TimeoutExpired:
        raise Exception("Conversion timed out (>60 seconds)")
    except subprocess.CalledProcessError as e:
        raise Exception(f"LibreOffice conversion failed: {e.stderr.decode() if e.stderr else str(e)}")
    except Exception as e:
        raise Exception(f"Failed to convert Word to PDF: {str(e)}")


# ==================== Excel to PDF ====================

def excel_to_pdf(xlsx_path: str, output_name: str = None) -> str:
    """
    Convert Excel spreadsheet to PDF using LibreOffice

    Args:
        xlsx_path: Path to Excel file
        output_name: Optional output filename

    Returns:
        Path to generated PDF file
    """
    try:
        import subprocess

        # Validate file exists
        if not os.path.exists(xlsx_path):
            raise Exception(f"Excel file not found: {xlsx_path}")

        # Generate output name
        if not output_name:
            xlsx_name = pathlib.Path(xlsx_path).stem
            output_name = f"{xlsx_name}_converted.pdf"

        if not output_name.endswith('.pdf'):
            output_name += '.pdf'

        output_path = os.path.join(DOCUMENTS_DIR, output_name)

        # Use LibreOffice to convert to PDF
        subprocess.run([
            'libreoffice',
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', DOCUMENTS_DIR,
            xlsx_path
        ], check=True, capture_output=True, timeout=60)

        # LibreOffice creates the file with original name + .pdf extension
        temp_output = os.path.join(DOCUMENTS_DIR, pathlib.Path(xlsx_path).stem + '.pdf')
        if temp_output != output_path and os.path.exists(temp_output):
            os.rename(temp_output, output_path)

        return output_path

    except subprocess.TimeoutExpired:
        raise Exception("Conversion timed out (>60 seconds)")
    except subprocess.CalledProcessError as e:
        raise Exception(f"LibreOffice conversion failed: {e.stderr.decode() if e.stderr else str(e)}")
    except Exception as e:
        raise Exception(f"Failed to convert Excel to PDF: {str(e)}")


# ==================== PowerPoint to PDF ====================

def powerpoint_to_pdf(pptx_path: str, output_name: str = None) -> str:
    """
    Convert PowerPoint presentation to PDF using LibreOffice

    Args:
        pptx_path: Path to PowerPoint file
        output_name: Optional output filename

    Returns:
        Path to generated PDF file
    """
    try:
        import subprocess

        # Validate file exists
        if not os.path.exists(pptx_path):
            raise Exception(f"PowerPoint file not found: {pptx_path}")

        # Generate output name
        if not output_name:
            pptx_name = pathlib.Path(pptx_path).stem
            output_name = f"{pptx_name}_converted.pdf"

        if not output_name.endswith('.pdf'):
            output_name += '.pdf'

        output_path = os.path.join(DOCUMENTS_DIR, output_name)

        # Use LibreOffice to convert to PDF
        subprocess.run([
            'libreoffice',
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', DOCUMENTS_DIR,
            pptx_path
        ], check=True, capture_output=True, timeout=60)

        # LibreOffice creates the file with original name + .pdf extension
        temp_output = os.path.join(DOCUMENTS_DIR, pathlib.Path(pptx_path).stem + '.pdf')
        if temp_output != output_path and os.path.exists(temp_output):
            os.rename(temp_output, output_path)

        return output_path

    except subprocess.TimeoutExpired:
        raise Exception("Conversion timed out (>60 seconds)")
    except subprocess.CalledProcessError as e:
        raise Exception(f"LibreOffice conversion failed: {e.stderr.decode() if e.stderr else str(e)}")
    except Exception as e:
        raise Exception(f"Failed to convert PowerPoint to PDF: {str(e)}")


# ==================== Utility Functions ====================

def get_pdf_info(pdf_path: str) -> dict:
    """Get information about a PDF file"""
    try:
        doc = fitz.open(pdf_path)
        info = {
            'pages': len(doc),
            'metadata': doc.metadata,
            'size_bytes': os.path.getsize(pdf_path),
            'encrypted': doc.is_encrypted
        }
        doc.close()
        return info
    except Exception as e:
        return {'error': str(e)}


def validate_file_type(file_path: str, allowed_extensions: List[str]) -> bool:
    """Validate if file has an allowed extension"""
    ext = pathlib.Path(file_path).suffix.lower()
    return ext in [f'.{e}' if not e.startswith('.') else e for e in allowed_extensions]


# ==================== PDF Merge ====================

def merge_pdfs(pdf_paths: List[str], output_name: str = None) -> str:
    """
    Merge multiple PDF files into a single PDF

    Args:
        pdf_paths: List of PDF file paths to merge
        output_name: Optional output filename

    Returns:
        Path to merged PDF file
    """
    try:
        if not pdf_paths or len(pdf_paths) == 0:
            raise Exception("No PDF files provided for merging")

        # Validate all files exist and are PDFs
        for pdf_path in pdf_paths:
            if not os.path.exists(pdf_path):
                raise Exception(f"PDF file not found: {pdf_path}")
            if not pdf_path.lower().endswith('.pdf'):
                raise Exception(f"Not a PDF file: {pdf_path}")

        # Generate output name if not provided
        if not output_name:
            output_name = f"merged_{int(time.time())}.pdf"

        if not output_name.endswith('.pdf'):
            output_name += '.pdf'

        output_path = os.path.join(DOCUMENTS_DIR, output_name)

        # Create PDF writer for merging
        writer = pypdf.PdfWriter()

        # Add each PDF
        for pdf_path in pdf_paths:
            print(f"Adding PDF to merge: {pdf_path}")
            reader = pypdf.PdfReader(pdf_path)
            for page in reader.pages:
                writer.add_page(page)

        # Write merged PDF
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)

        print(f"Successfully merged {len(pdf_paths)} PDFs into: {output_path}")
        return output_path

    except Exception as e:
        raise Exception(f"Failed to merge PDFs: {str(e)}")


# Add time import that was missing
import time

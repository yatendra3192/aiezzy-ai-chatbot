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
    Preserves tables and basic formatting

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

        # Process each page
        for page_num in range(len(doc_pdf)):
            page = doc_pdf[page_num]

            # Add page break after first page
            if page_num > 0:
                doc_word.add_page_break()

            # Find tables on page using PyMuPDF's table detection
            try:
                tables = page.find_tables()

                if tables and len(tables.tables) > 0:
                    # Page contains tables
                    print(f"Found {len(tables.tables)} tables on page {page_num + 1}")

                    # Get all text blocks with their positions
                    blocks = page.get_text("dict")["blocks"]
                    text_blocks = []

                    for block in blocks:
                        if block.get("type") == 0:  # Text block
                            bbox = block["bbox"]
                            text = ""
                            for line in block.get("lines", []):
                                for span in line.get("spans", []):
                                    text += span.get("text", "")
                                text += "\n"
                            if text.strip():
                                text_blocks.append({
                                    "bbox": bbox,
                                    "text": text.strip(),
                                    "y0": bbox[1]  # Top Y coordinate for sorting
                                })

                    # Sort blocks by vertical position
                    text_blocks.sort(key=lambda x: x["y0"])

                    # Process tables and text in order
                    table_bboxes = []
                    for table in tables.tables:
                        bbox = table.bbox
                        table_bboxes.append({
                            "bbox": bbox,
                            "table": table,
                            "y0": bbox[1]
                        })

                    # Combine and sort all elements
                    all_elements = text_blocks + table_bboxes
                    all_elements.sort(key=lambda x: x["y0"])

                    # Add elements to Word doc in order
                    for element in all_elements:
                        if "table" in element:
                            # Add table to Word
                            table = element["table"]
                            table_data = table.extract()

                            if table_data and len(table_data) > 0:
                                # Create Word table
                                rows = len(table_data)
                                cols = max(len(row) for row in table_data) if table_data else 0

                                if rows > 0 and cols > 0:
                                    word_table = doc_word.add_table(rows=rows, cols=cols)
                                    word_table.style = 'Table Grid'

                                    # Fill table cells
                                    for i, row in enumerate(table_data):
                                        for j, cell in enumerate(row):
                                            if j < cols and cell:
                                                word_table.rows[i].cells[j].text = str(cell)
                        else:
                            # Add text paragraph
                            if element["text"].strip():
                                doc_word.add_paragraph(element["text"])

                else:
                    # No tables found, extract text normally
                    text = page.get_text()
                    if text.strip():
                        doc_word.add_paragraph(text)

            except Exception as table_error:
                print(f"Table detection failed on page {page_num + 1}: {table_error}")
                # Fallback to plain text extraction
                text = page.get_text()
                if text.strip():
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
    Preserves table structure and formatting

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

        current_row = 1

        # Process each page
        for page_num in range(len(doc)):
            page = doc[page_num]

            # Add page header
            ws.cell(row=current_row, column=1, value=f"Page {page_num + 1}")
            ws.cell(row=current_row, column=1).font = ws.cell(row=current_row, column=1).font.copy(bold=True)
            current_row += 1

            # Try to find tables on the page
            try:
                tables = page.find_tables()

                if tables and len(tables.tables) > 0:
                    # Page contains tables
                    print(f"Found {len(tables.tables)} tables on page {page_num + 1}")

                    for table_idx, table in enumerate(tables.tables):
                        table_data = table.extract()

                        if table_data and len(table_data) > 0:
                            # Add table to Excel with proper structure
                            start_row = current_row

                            for row_idx, row in enumerate(table_data):
                                for col_idx, cell in enumerate(row):
                                    if cell:
                                        ws.cell(row=current_row, column=col_idx + 1, value=str(cell))

                                        # Bold header row if first row
                                        if row_idx == 0:
                                            ws.cell(row=current_row, column=col_idx + 1).font = \
                                                ws.cell(row=current_row, column=col_idx + 1).font.copy(bold=True)

                                current_row += 1

                            current_row += 1  # Add space after table

                            # Auto-adjust column widths for table
                            for col_idx in range(len(table_data[0]) if table_data else 0):
                                col_letter = ws.cell(row=start_row, column=col_idx + 1).column_letter
                                max_length = 0
                                for row_idx in range(start_row, current_row - 1):
                                    cell_value = ws.cell(row=row_idx, column=col_idx + 1).value
                                    if cell_value:
                                        max_length = max(max_length, len(str(cell_value)))
                                ws.column_dimensions[col_letter].width = min(max_length + 2, 50)

                else:
                    # No tables found, extract text normally
                    text = page.get_text()
                    lines = text.split('\n')
                    for line in lines:
                        if line.strip():
                            ws.cell(row=current_row, column=1, value=line)
                            current_row += 1

            except Exception as table_error:
                print(f"Table detection failed on page {page_num + 1}: {table_error}")
                # Fallback to plain text extraction
                text = page.get_text()
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


# ==================== Excel to CSV ====================

def excel_to_csv(xlsx_path: str, output_name: str = None, sheet_name: str = None) -> str:
    """
    Convert Excel spreadsheet to CSV format using LibreOffice

    Args:
        xlsx_path: Path to Excel file
        output_name: Optional output filename (without extension)
        sheet_name: Optional specific sheet to convert (default: first sheet)

    Returns:
        Path to generated CSV file
    """
    try:
        import subprocess

        # Validate file exists
        if not os.path.exists(xlsx_path):
            raise Exception(f"Excel file not found: {xlsx_path}")

        # Generate output name
        if not output_name:
            xlsx_name = pathlib.Path(xlsx_path).stem
            output_name = f"{xlsx_name}_converted.csv"

        if not output_name.endswith('.csv'):
            output_name += '.csv'

        output_path = os.path.join(DOCUMENTS_DIR, output_name)

        # Use LibreOffice to convert to CSV
        # --infilter for Excel input, --convert-to for CSV output
        subprocess.run([
            'libreoffice',
            '--headless',
            '--convert-to', 'csv',
            '--outdir', DOCUMENTS_DIR,
            xlsx_path
        ], check=True, capture_output=True, timeout=60)

        # LibreOffice creates the file with original name + .csv extension
        temp_output = os.path.join(DOCUMENTS_DIR, pathlib.Path(xlsx_path).stem + '.csv')
        if temp_output != output_path and os.path.exists(temp_output):
            os.rename(temp_output, output_path)

        return output_path

    except subprocess.TimeoutExpired:
        raise Exception("Conversion timed out (>60 seconds)")
    except subprocess.CalledProcessError as e:
        raise Exception(f"LibreOffice conversion failed: {e.stderr.decode() if e.stderr else str(e)}")
    except Exception as e:
        raise Exception(f"Failed to convert Excel to CSV: {str(e)}")


# ==================== CSV to Excel ====================

def csv_to_excel(csv_path: str, output_name: str = None) -> str:
    """
    Convert CSV file to Excel spreadsheet using LibreOffice

    Args:
        csv_path: Path to CSV file
        output_name: Optional output filename (without extension)

    Returns:
        Path to generated Excel file
    """
    try:
        import subprocess

        # Validate file exists
        if not os.path.exists(csv_path):
            raise Exception(f"CSV file not found: {csv_path}")

        # Generate output name
        if not output_name:
            csv_name = pathlib.Path(csv_path).stem
            output_name = f"{csv_name}_converted.xlsx"

        if not output_name.endswith('.xlsx'):
            output_name += '.xlsx'

        output_path = os.path.join(DOCUMENTS_DIR, output_name)

        # Use LibreOffice to convert CSV to Excel
        subprocess.run([
            'libreoffice',
            '--headless',
            '--convert-to', 'xlsx',
            '--outdir', DOCUMENTS_DIR,
            csv_path
        ], check=True, capture_output=True, timeout=60)

        # LibreOffice creates the file with original name + .xlsx extension
        temp_output = os.path.join(DOCUMENTS_DIR, pathlib.Path(csv_path).stem + '.xlsx')
        if temp_output != output_path and os.path.exists(temp_output):
            os.rename(temp_output, output_path)

        return output_path

    except subprocess.TimeoutExpired:
        raise Exception("Conversion timed out (>60 seconds)")
    except subprocess.CalledProcessError as e:
        raise Exception(f"LibreOffice conversion failed: {e.stderr.decode() if e.stderr else str(e)}")
    except Exception as e:
        raise Exception(f"Failed to convert CSV to Excel: {str(e)}")


# ==================== Word to TXT ====================

def word_to_txt(docx_path: str, output_name: str = None) -> str:
    """
    Convert Word document to plain text format using LibreOffice

    Args:
        docx_path: Path to Word file
        output_name: Optional output filename (without extension)

    Returns:
        Path to generated TXT file
    """
    try:
        import subprocess

        # Validate file exists
        if not os.path.exists(docx_path):
            raise Exception(f"Word file not found: {docx_path}")

        # Generate output name
        if not output_name:
            docx_name = pathlib.Path(docx_path).stem
            output_name = f"{docx_name}_converted.txt"

        if not output_name.endswith('.txt'):
            output_name += '.txt'

        output_path = os.path.join(DOCUMENTS_DIR, output_name)

        # Use LibreOffice to convert to TXT
        subprocess.run([
            'libreoffice',
            '--headless',
            '--convert-to', 'txt',
            '--outdir', DOCUMENTS_DIR,
            docx_path
        ], check=True, capture_output=True, timeout=60)

        # LibreOffice creates the file with original name + .txt extension
        temp_output = os.path.join(DOCUMENTS_DIR, pathlib.Path(docx_path).stem + '.txt')
        if temp_output != output_path and os.path.exists(temp_output):
            os.rename(temp_output, output_path)

        return output_path

    except subprocess.TimeoutExpired:
        raise Exception("Conversion timed out (>60 seconds)")
    except subprocess.CalledProcessError as e:
        raise Exception(f"LibreOffice conversion failed: {e.stderr.decode() if e.stderr else str(e)}")
    except Exception as e:
        raise Exception(f"Failed to convert Word to TXT: {str(e)}")


# ==================== Excel to TXT ====================

def excel_to_txt(xlsx_path: str, output_name: str = None) -> str:
    """
    Convert Excel spreadsheet to plain text format using LibreOffice

    Args:
        xlsx_path: Path to Excel file
        output_name: Optional output filename (without extension)

    Returns:
        Path to generated TXT file
    """
    try:
        import subprocess

        # Validate file exists
        if not os.path.exists(xlsx_path):
            raise Exception(f"Excel file not found: {xlsx_path}")

        # Generate output name
        if not output_name:
            xlsx_name = pathlib.Path(xlsx_path).stem
            output_name = f"{xlsx_name}_converted.txt"

        if not output_name.endswith('.txt'):
            output_name += '.txt'

        output_path = os.path.join(DOCUMENTS_DIR, output_name)

        # Use LibreOffice to convert to TXT
        subprocess.run([
            'libreoffice',
            '--headless',
            '--convert-to', 'txt',
            '--outdir', DOCUMENTS_DIR,
            xlsx_path
        ], check=True, capture_output=True, timeout=60)

        # LibreOffice creates the file with original name + .txt extension
        temp_output = os.path.join(DOCUMENTS_DIR, pathlib.Path(xlsx_path).stem + '.txt')
        if temp_output != output_path and os.path.exists(temp_output):
            os.rename(temp_output, output_path)

        return output_path

    except subprocess.TimeoutExpired:
        raise Exception("Conversion timed out (>60 seconds)")
    except subprocess.CalledProcessError as e:
        raise Exception(f"LibreOffice conversion failed: {e.stderr.decode() if e.stderr else str(e)}")
    except Exception as e:
        raise Exception(f"Failed to convert Excel to TXT: {str(e)}")


# ==================== Word to HTML ====================

def word_to_html(docx_path: str, output_name: str = None) -> str:
    """
    Convert Word document to HTML format using LibreOffice

    Args:
        docx_path: Path to Word file
        output_name: Optional output filename (without extension)

    Returns:
        Path to generated HTML file
    """
    try:
        import subprocess

        # Validate file exists
        if not os.path.exists(docx_path):
            raise Exception(f"Word file not found: {docx_path}")

        # Generate output name
        if not output_name:
            docx_name = pathlib.Path(docx_path).stem
            output_name = f"{docx_name}_converted.html"

        if not output_name.endswith('.html'):
            output_name += '.html'

        output_path = os.path.join(DOCUMENTS_DIR, output_name)

        # Use LibreOffice to convert to HTML
        subprocess.run([
            'libreoffice',
            '--headless',
            '--convert-to', 'html',
            '--outdir', DOCUMENTS_DIR,
            docx_path
        ], check=True, capture_output=True, timeout=60)

        # LibreOffice creates the file with original name + .html extension
        temp_output = os.path.join(DOCUMENTS_DIR, pathlib.Path(docx_path).stem + '.html')
        if temp_output != output_path and os.path.exists(temp_output):
            os.rename(temp_output, output_path)

        return output_path

    except subprocess.TimeoutExpired:
        raise Exception("Conversion timed out (>60 seconds)")
    except subprocess.CalledProcessError as e:
        raise Exception(f"LibreOffice conversion failed: {e.stderr.decode() if e.stderr else str(e)}")
    except Exception as e:
        raise Exception(f"Failed to convert Word to HTML: {str(e)}")


# ==================== Excel to HTML ====================

def excel_to_html(xlsx_path: str, output_name: str = None) -> str:
    """
    Convert Excel spreadsheet to HTML format using LibreOffice

    Args:
        xlsx_path: Path to Excel file
        output_name: Optional output filename (without extension)

    Returns:
        Path to generated HTML file
    """
    try:
        import subprocess

        # Validate file exists
        if not os.path.exists(xlsx_path):
            raise Exception(f"Excel file not found: {xlsx_path}")

        # Generate output name
        if not output_name:
            xlsx_name = pathlib.Path(xlsx_path).stem
            output_name = f"{xlsx_name}_converted.html"

        if not output_name.endswith('.html'):
            output_name += '.html'

        output_path = os.path.join(DOCUMENTS_DIR, output_name)

        # Use LibreOffice to convert to HTML
        subprocess.run([
            'libreoffice',
            '--headless',
            '--convert-to', 'html',
            '--outdir', DOCUMENTS_DIR,
            xlsx_path
        ], check=True, capture_output=True, timeout=60)

        # LibreOffice creates the file with original name + .html extension
        temp_output = os.path.join(DOCUMENTS_DIR, pathlib.Path(xlsx_path).stem + '.html')
        if temp_output != output_path and os.path.exists(temp_output):
            os.rename(temp_output, output_path)

        return output_path

    except subprocess.TimeoutExpired:
        raise Exception("Conversion timed out (>60 seconds)")
    except subprocess.CalledProcessError as e:
        raise Exception(f"LibreOffice conversion failed: {e.stderr.decode() if e.stderr else str(e)}")
    except Exception as e:
        raise Exception(f"Failed to convert Excel to HTML: {str(e)}")


# ==================== PowerPoint to HTML ====================

def powerpoint_to_html(pptx_path: str, output_name: str = None) -> str:
    """
    Convert PowerPoint presentation to HTML format using LibreOffice

    Args:
        pptx_path: Path to PowerPoint file
        output_name: Optional output filename (without extension)

    Returns:
        Path to generated HTML file
    """
    try:
        import subprocess

        # Validate file exists
        if not os.path.exists(pptx_path):
            raise Exception(f"PowerPoint file not found: {pptx_path}")

        # Generate output name
        if not output_name:
            pptx_name = pathlib.Path(pptx_path).stem
            output_name = f"{pptx_name}_converted.html"

        if not output_name.endswith('.html'):
            output_name += '.html'

        output_path = os.path.join(DOCUMENTS_DIR, output_name)

        # Use LibreOffice to convert to HTML
        subprocess.run([
            'libreoffice',
            '--headless',
            '--convert-to', 'html',
            '--outdir', DOCUMENTS_DIR,
            pptx_path
        ], check=True, capture_output=True, timeout=60)

        # LibreOffice creates the file with original name + .html extension
        temp_output = os.path.join(DOCUMENTS_DIR, pathlib.Path(pptx_path).stem + '.html')
        if temp_output != output_path and os.path.exists(temp_output):
            os.rename(temp_output, output_path)

        return output_path

    except subprocess.TimeoutExpired:
        raise Exception("Conversion timed out (>60 seconds)")
    except subprocess.CalledProcessError as e:
        raise Exception(f"LibreOffice conversion failed: {e.stderr.decode() if e.stderr else str(e)}")
    except Exception as e:
        raise Exception(f"Failed to convert PowerPoint to HTML: {str(e)}")

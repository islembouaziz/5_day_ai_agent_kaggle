import io
from pypdf import PdfReader
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract plain text from a PDF file given as raw bytes.

    Args:
        file_bytes: The raw bytes of the uploaded PDF.

    Returns:
        A single string containing all extracted text, cleaned up.

    Raises:
        ValueError: If the PDF cannot be opened or yields no text.
    """
    try:
        pdf_stream = io.BytesIO(file_bytes)
        reader = PdfReader(pdf_stream)
        logger.info("Successfully loaded PDF stream.")
    except Exception as exc:
        logger.error(f"Failed to open PDF stream: {exc}")
        raise ValueError(f"Could not open PDF: {exc}") from exc

    pages_text: list[str] = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text and text.strip():
            pages_text.append(text.strip())
            
    logger.info(f"Extracted text from {len(pages_text)} pages.")

    full_text = "\n\n".join(pages_text)

    if not full_text.strip():
        logger.warning("No text could be extracted from this PDF.")
        raise ValueError(
            "No text could be extracted from this PDF. "
            "It may be a scanned image — please use a text-based PDF."
        )

    return full_text

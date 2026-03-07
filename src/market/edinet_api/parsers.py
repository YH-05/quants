"""Parsers for EDINET disclosure API document files.

This module provides functions for extracting content from EDINET
disclosure document ZIP archives, including XBRL files and PDF files.

Functions
---------
parse_xbrl_zip
    Extract and parse XBRL files from a ZIP archive.
extract_pdf
    Extract a PDF file from a ZIP archive.

Notes
-----
EDINET disclosure documents are distributed as ZIP archives containing
XBRL files (for structured data) and/or PDF files (for human-readable
documents). This module handles the extraction of these files from
the ZIP archives.

See Also
--------
market.edinet_api.client : Downloads document archives from the EDINET API.
"""

import io
import posixpath
import zipfile

from utils_core.logging import get_logger

logger = get_logger(__name__)


def parse_xbrl_zip(data: bytes) -> dict[str, bytes]:
    """Extract XBRL files from a ZIP archive.

    Reads a ZIP archive (as raw bytes) and extracts all files with
    XBRL-related extensions (``.xbrl``, ``.xml``, ``.xsd``).

    Parameters
    ----------
    data : bytes
        Raw bytes of a ZIP archive containing XBRL files.

    Returns
    -------
    dict[str, bytes]
        Dictionary mapping filenames to their raw content bytes.
        Only files with XBRL-related extensions are included.

    Raises
    ------
    ValueError
        If ``data`` is empty.
    zipfile.BadZipFile
        If ``data`` is not a valid ZIP archive.

    Examples
    --------
    >>> files = parse_xbrl_zip(zip_bytes)
    >>> for name, content in files.items():
    ...     print(f"{name}: {len(content)} bytes")
    """
    if not data:
        raise ValueError("data must not be empty")

    logger.debug("Parsing XBRL ZIP archive", data_length=len(data))

    xbrl_extensions = (".xbrl", ".xml", ".xsd")
    result: dict[str, bytes] = {}

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for info in zf.infolist():
            # Skip directories
            if info.is_dir():
                continue

            # Zip Slip prevention (CWE-22): sanitize filename
            safe_name = posixpath.normpath(info.filename).lstrip("/")
            if safe_name.startswith(".."):
                logger.warning("Skipping suspicious path", filename=info.filename)
                continue

            # Extract files with XBRL-related extensions
            lower_name = safe_name.lower()
            if any(lower_name.endswith(ext) for ext in xbrl_extensions):
                result[safe_name] = zf.read(info.filename)

    logger.info(
        "XBRL ZIP parsing completed",
        total_entries=len(result),
        xbrl_files_extracted=len(result),
    )
    return result


def extract_pdf(data: bytes) -> bytes:
    """Extract a PDF file from a ZIP archive.

    Reads a ZIP archive (as raw bytes) and extracts the first file
    with a ``.pdf`` extension.

    Parameters
    ----------
    data : bytes
        Raw bytes of a ZIP archive containing a PDF file.

    Returns
    -------
    bytes
        Raw content of the extracted PDF file.

    Raises
    ------
    ValueError
        If ``data`` is empty or no PDF file is found in the archive.
    zipfile.BadZipFile
        If ``data`` is not a valid ZIP archive.

    Examples
    --------
    >>> pdf_content = extract_pdf(zip_bytes)
    >>> len(pdf_content) > 0
    True
    """
    if not data:
        raise ValueError("data must not be empty")

    logger.debug("Extracting PDF from ZIP archive", data_length=len(data))

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue

            # Zip Slip prevention (CWE-22)
            safe_name = posixpath.normpath(info.filename).lstrip("/")
            if safe_name.startswith(".."):
                logger.warning("Skipping suspicious path", filename=info.filename)
                continue

            if safe_name.lower().endswith(".pdf"):
                content = zf.read(info.filename)
                logger.info(
                    "PDF extracted",
                    filename=info.filename,
                    content_length=len(content),
                )
                return content

    raise ValueError("No PDF file found in ZIP archive")


__all__ = ["extract_pdf", "parse_xbrl_zip"]

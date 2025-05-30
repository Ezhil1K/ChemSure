import logging
import re
import pdfplumber
from pdf2image import convert_from_bytes
import pytesseract
import pandas as pd
from PIL import ImageEnhance, ImageFilter
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- IMPORTANT: Tesseract OCR and Poppler PDF utilities are required ---
# Ensure Tesseract is installed and its path is in your system's PATH variable.
# For Windows, you might need to install Poppler for pdf2image to work.
# Example for Tesseract cmd path (uncomment and adjust if needed):
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# ---

# Define the path to your GADSL Excel file (relative to this script's directory)
GADSL_FILE_NAME = "GADSL-Reference-List.xlsx"
GADSL_FILE_PATH = os.path.join(os.path.dirname(__file__), GADSL_FILE_NAME)

# Internal global variables to store GADSL data for efficient lookups
_gadsl_data_by_cas = None
_gadsl_data_by_name = None

def load_gadsl_data():
    """Load GADSL dataset into memory, creating two lookup dictionaries."""
    global _gadsl_data_by_cas, _gadsl_data_by_name
    
    temp_gadsl_by_cas = {}
    temp_gadsl_by_name = {}

    try:
        logger.info(f"Loading GADSL data from: {GADSL_FILE_PATH}")
        df = pd.read_excel(GADSL_FILE_PATH)

        # --- MODIFICATION: EXCLUDING 'Effective date' COLUMN ---
        df.rename(columns={
            'GADSL #': "gadsl_hash",
            'REF #': "ref_hash",
            'Substance': "substance_name",
            'CAS RN': "cas_rn",
            'Classification': "classification",
            'Reason Code': "reason_code",
            'Source\n(Legal requirements, regulations)': "source",
            # 'Effective date (Legal requirements, regulations)\n Date           |        Action required' is EXCLUDED
            'Generic examples': "generic_examples",
            'Reporting threshold\n(0.1% unless otherwise stated)': "reporting_threshold",
            'First added': "first_added",
            'Last revised': "last_revised"
        }, inplace=True)
        # --- END MODIFICATION ---

        # Define all expected column names AFTER renaming
        required_columns_check = [
            "gadsl_hash", "ref_hash", "substance_name", "cas_rn", 
            "classification", "reason_code", "source", 
            "generic_examples", "reporting_threshold", "first_added", "last_revised"
        ]
        
        # Check if the DataFrame is empty or if any required columns are missing after renaming
        if df.empty or not all(col in df.columns for col in required_columns_check):
            missing_cols = [col for col in required_columns_check if col not in df.columns]
            raise ValueError(f"GADSL file is empty or missing one or more required columns after renaming. Missing: {missing_cols}")

        for _, row in df.iterrows():
            cas_rn = str(row.get("cas_rn")).strip() if pd.notna(row.get("cas_rn")) else None
            substance_name = str(row.get("substance_name")).strip() if pd.notna(row.get("substance_name")) else None

            entry_data = {
                "gadsl_hash": (str(row.get("gadsl_hash")).strip() if pd.notna(row.get("gadsl_hash")) else "N/A"),
                "ref_hash": (str(row.get("ref_hash")).strip() if pd.notna(row.get("ref_hash")) else "N/A"),
                "substance_name": (substance_name if substance_name else "N/A"), # Keep original case for display
                "cas_rn": (cas_rn if cas_rn else "N/A"),
                "classification": (str(row.get("classification")).strip() if pd.notna(row.get("classification")) else "N/A"),
                "reason_code": (str(row.get("reason_code")).strip() if pd.notna(row.get("reason_code")) else "N/A"),
                "source": (str(row.get("source")).strip() if pd.notna(row.get("source")) else "N/A"),
                "generic_examples": (str(row.get("generic_examples")).strip() if pd.notna(row.get("generic_examples")) else "N/A"),
                "reporting_threshold": (str(row.get("reporting_threshold")).strip() if pd.notna(row.get("reporting_threshold")) else "0.1%"), # Default to 0.1%
                "first_added": (str(row.get("first_added")).strip() if pd.notna(row.get("first_added")) else "N/A"),
                "last_revised": (str(row.get("last_revised")).strip() if pd.notna(row.get("last_revised")) else "N/A")
            }
            
            # Store with consistent keys for lookup (stripped CAS, lowercased name)
            if cas_rn and cas_rn != "N/A":
                temp_gadsl_by_cas[cas_rn] = entry_data
            if substance_name and substance_name != "N/A":
                # Ensure substance names are stored in lowercase for robust matching
                temp_gadsl_by_name[substance_name.lower()] = entry_data

        # Assign to the global variables ONLY AFTER successful processing
        _gadsl_data_by_cas = temp_gadsl_by_cas
        _gadsl_data_by_name = temp_gadsl_by_name
        
        logger.info(f"✅ Successfully loaded {len(_gadsl_data_by_cas)} entries (by CAS) and {len(_gadsl_data_by_name)} entries (by Name)!")
    except FileNotFoundError:
        logger.error(f"Error: GADSL file not found at {GADSL_FILE_PATH}")
        _gadsl_data_by_cas = None
        _gadsl_data_by_name = None
        raise # Re-raise to indicate critical startup failure
    except Exception as e:
        logger.error(f"Error loading GADSL data: {str(e)}", exc_info=True)
        _gadsl_data_by_cas = None
        _gadsl_data_by_name = None
        raise # Re-raise to indicate critical startup failure

# --- Functions to expose the loaded data to other modules ---
def get_gadsl_data_by_cas():
    """Returns the loaded CAS lookup dictionary."""
    return _gadsl_data_by_cas

def get_gadsl_data_by_name():
    """Returns the loaded Substance Name lookup dictionary."""
    return _gadsl_data_by_name

# --- Lookup functions use the getter functions to access data ---
def lookup_by_cas_rn(cas_rn):
    """Search GADSL data by CAS number."""
    data = get_gadsl_data_by_cas()
    if data is None:
        logger.error("GADSL data not loaded for CAS lookup.")
        return {"error": "GADSL data not loaded on server."} # Return a proper error dict
    
    # Ensure consistency in lookup key: strip whitespace
    result = data.get(cas_rn.strip())
    if result:
        return result
    else:
        return None # Return None if not found, let Flask handle the "not found" response

def lookup_by_substance_name(substance_name):
    """Search GADSL data by substance name."""
    data = get_gadsl_data_by_name()
    if data is None:
        logger.error("GADSL data not loaded for substance name lookup.")
        return {"error": "GADSL data not loaded on server."} # Return a proper error dict
    
    # Ensure consistency in lookup key: lower and strip
    result = data.get(substance_name.lower().strip())
    if result:
        return result
    else:
        return None # Return None if not found

def preprocess_image(image):
    """Enhance image quality for better OCR recognition."""
    image = image.convert("L") # Convert to grayscale
    image = image.filter(ImageFilter.SHARPEN)
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2) # Increase contrast
    return image

def process_msds_pdf_for_gadsl_matches(pdf_file_stream):
    """Extract CAS numbers & substance names from PDF and match against GADSL dataset."""
    cas_data = get_gadsl_data_by_cas()
    name_data = get_gadsl_data_by_name()

    if cas_data is None or name_data is None:
        logger.error("GADSL data not loaded for PDF processing.")
        raise ValueError("GADSL data not loaded on server for PDF processing.")

    matches = []
    processed_cas_rns = set() # Use CAS RN to track unique matches for PDF

    try:
        full_text = ""
        # Attempt text extraction with pdfplumber first
        try:
            with pdfplumber.open(pdf_file_stream) as pdf:
                # Concatenate text from all pages
                full_text = "\n".join([page.extract_text() or "" for page in pdf.pages])
        except Exception as e:
            logger.warning(f"pdfplumber failed to extract text (might be scanned PDF): {e}")

        # If pdfplumber yields little to no text, try OCR
        if not full_text.strip() or len(full_text.strip()) < 50:
            logger.info("Insufficient text detected with pdfplumber, attempting OCR...")
            pdf_file_stream.seek(0) # Reset stream position for pdf2image
            
            pdf_bytes = pdf_file_stream.read()
            images = convert_from_bytes(pdf_bytes, dpi=300) # Higher DPI for better OCR
            full_text = "\n".join([pytesseract.image_to_string(preprocess_image(img)) for img in images])
            logger.info("OCR text extraction complete.")

        if not full_text.strip():
            logger.warning("No searchable text found in PDF even after OCR.")
            return []

        # Focus search on Section 3, if present, otherwise search whole document
        section_3_pattern = re.compile(
            r"SECTION\s*3[:\s]*Composition/Information(?:.*?)on Ingredients.*?SECTION\s*4[:\s]*First Aid Measures",
            re.IGNORECASE | re.DOTALL
        )
        section_3_match = section_3_pattern.search(full_text)
        
        section_text = full_text
        if section_3_match:
            section_text = section_3_match.group(0)
            logger.info("SECTION 3 identified for detailed parsing.")
        else:
            logger.info("SECTION 3 not found, searching entire document.")

        # --- Extract CAS numbers ---
        # CAS RN pattern: digits-digits-digit (e.g., 75-07-0, 1333-82-0, 13463-67-7)
        cas_numbers_found = re.findall(r"\b\d{2,7}-\d{2}-\d\b", section_text)
        
        # --- Extract potential substance names (improved regex) ---
        # Looks for sequences of capitalized words, possibly with hyphens or numbers (e.g., Benzoic Acid, 1,2-Dichloroethane)
        # Excludes short common words or purely numeric/percentage values
        substance_names_found = re.findall(
            r"\b(?:[A-Z][a-z0-9]+(?:[\s-][A-Z]?[a-z0-9]+)*|\d{1,3}(?:,\d{3})*(?:\.\d+)?(?:-\d{1,3})?)\b(?:[\s-]\b[A-Z][a-z0-9]+(?:[\s-][A-Z]?[a-z0-9]+)*\b)*",
            section_text
        )
        
        # Filter common words and single characters that are not real substance names
        common_words_to_exclude = {
            "section", "table", "page", "figure", "date", "version", "composition", 
            "information", "ingredients", "measure", "first", "health", "safety", "data",
            "sheet", "product", "chemical", "hazard", "identification", "handling", "storage",
            "exposure", "protection", "physical", "properties", "stability", "reactivity",
            "toxicological", "ecological", "disposal", "considerations", "transport", "regulatory",
            "other", "company", "address", "phone", "fax", "email"
        }
        substance_names_found = [
            name.strip() for name in substance_names_found 
            if len(name.strip()) > 3 # Minimum length
            and not re.fullmatch(r"^\d+(\.\d+)?%$", name.strip()) # Exclude percentages
            and not re.fullmatch(r"^\d+$", name.strip()) # Exclude pure numbers
            and name.strip().lower() not in common_words_to_exclude # Exclude common words
        ]
        
        # Consolidate and make unique for efficient lookup
        unique_identifiers = set()
        for cas in cas_numbers_found:
            unique_identifiers.add(cas.strip())
        for name in substance_names_found:
            unique_identifiers.add(name.lower().strip()) # Store names in lowercase for lookup

        for identifier in unique_identifiers:
            result = None
            if re.fullmatch(r"\b\d{2,7}-\d{2}-\d\b", identifier):
                # This is a CAS RN, lookup in CAS data
                result = lookup_by_cas_rn(identifier)
            else:
                # Treat as substance name, lookup in name data (already lowercased for lookup)
                result = lookup_by_substance_name(identifier)
            
            if result and "error" not in result: # Ensure it's a valid result, not an error dict
                # Only add if we haven't already processed this CAS RN to avoid duplicates from multiple matches
                if result["cas_rn"] not in processed_cas_rns:
                    matches.append(result)
                    processed_cas_rns.add(result["cas_rn"])
                    logger.info(f"Match found in PDF: CAS RN {result['cas_rn']}, Name: {result['substance_name']}")

        logger.info(f"✅ Found {len(matches)} unique GADSL matches in PDF.")
        return matches
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}", exc_info=True)
        raise # Re-raise to be caught by the Flask endpoint
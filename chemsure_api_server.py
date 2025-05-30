from flask import Flask, request, jsonify, render_template
import logging
import os

# Import the necessary functions from your backend logic
from backend_gadsl_lookup_api import (
    load_gadsl_data, 
    lookup_by_cas_rn, 
    lookup_by_substance_name, 
    process_msds_pdf_for_gadsl_matches,
    get_gadsl_data_by_cas # Used for initial data load check
)

# Configure logging for the Flask application
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Attempt to load GADSL data on Flask app startup
# This ensures the data is available for all requests
try:
    logger.info("Attempting to load GADSL data for this Flask process...")
    load_gadsl_data()
    
    if get_gadsl_data_by_cas(): # Check if data was loaded successfully
        logger.info("GADSL data loaded successfully in this process context.")
    else:
        # This case should ideally not be reached if load_gadsl_data raises on error
        logger.warning("GADSL data failed to load in this process context, get_gadsl_data_by_cas() returned None.")
except Exception as e:
    logger.critical(f"CRITICAL ERROR: Failed to load GADSL data at startup for this process: {str(e)}. "
                    "All lookups will return 503.", exc_info=True)
    # You might want to exit or set a flag here to prevent the server from running
    # if data loading is absolutely critical and cannot be recovered.
    # For now, we'll let the endpoints return 503 if data is None.

# Route for the main page
@app.route("/")
def index():
    # Flask looks for templates in the 'templates' folder by default
    return render_template("index.html")

# API endpoint for searching by CAS RN
@app.route("/lookup_by_cas_rn", methods=["POST"])
def lookup_cas():
    try:
        # Check if GADSL data is loaded before attempting a lookup
        if get_gadsl_data_by_cas() is None:
            logger.error("Attempted CAS lookup, but GADSL data was not loaded.")
            return jsonify({"error": "Server data not ready. Please try again later (GADSL data failed to load)."}), 503

        data = request.get_json()
        if not data or "cas_rn" not in data:
            return jsonify({"error": "CAS number is required in the request body."}), 400
        
        cas_rn = data["cas_rn"]
        # Call the backend lookup function
        result = lookup_by_cas_rn(cas_rn)

        # Return the result as an array, even if empty, for consistency with frontend
        if result: # If a result was found (not None)
            return jsonify({"results": [result]})
        else: # If no result was found
            logger.info(f"CAS RN '{cas_rn}' not found in GADSL.")
            return jsonify({"results": []}) # Return an empty array
            
    except Exception as e:
        logger.error(f"Error in lookup_by_cas_rn endpoint for '{request.get_json().get('cas_rn', 'N/A')}': {str(e)}", exc_info=True)
        return jsonify({"error": "An internal server error occurred during CAS lookup. Please check the server logs."}), 500

# API endpoint for searching by Substance Name
@app.route("/lookup_by_substance_name", methods=["POST"])
def lookup_substance():
    try:
        # Check if GADSL data is loaded
        if get_gadsl_data_by_cas() is None: # Can use either cas or name data getter for this check
            logger.error("Attempted substance name lookup, but GADSL data was not loaded.")
            return jsonify({"error": "Server data not ready. Please try again later (GADSL data failed to load)."}), 503

        data = request.get_json()
        if not data or "substance_name" not in data:
            return jsonify({"error": "Substance name is required in the request body."}), 400
        
        substance_name = data["substance_name"]
        # Call the backend lookup function
        result = lookup_by_substance_name(substance_name)

        # Return the result as an array, even if empty
        if result: # If a result was found (not None)
            return jsonify({"results": [result]})
        else: # If no result was found
            logger.info(f"Substance name '{substance_name}' not found in GADSL.")
            return jsonify({"results": []}) # Return an empty array
            
    except Exception as e:
        logger.error(f"Error in lookup_by_substance_name endpoint for '{request.get_json().get('substance_name', 'N/A')}': {str(e)}", exc_info=True)
        return jsonify({"error": "An internal server error occurred during substance name lookup. Please check the server logs."}), 500

# API endpoint for uploading and processing MSDS PDFs
@app.route("/upload_msds_pdf", methods=["POST"])
def upload_msds_pdf():
    try:
        # Check if GADSL data is loaded
        if get_gadsl_data_by_cas() is None:
            logger.error("Attempted PDF upload, but GADSL data was not loaded.")
            return jsonify({"error": "Server data not ready. Please try again later (GADSL data failed to load)."}), 503

        if "msds_pdf" not in request.files:
            return jsonify({"error": "No PDF file provided in the request."}), 400

        pdf_file = request.files["msds_pdf"]
        if not pdf_file.filename or not pdf_file.filename.lower().endswith('.pdf'):
            return jsonify({"error": "Invalid file type. Only PDF files are allowed and a filename is required."}), 400

        # Pass the FileStorage object directly, it behaves like a file stream
        results = process_msds_pdf_for_gadsl_matches(pdf_file)

        # Always return a list of results, even if empty, for consistency
        return jsonify({"results": results if results else []})
        
    except ValueError as ve: # Catch specific validation errors from backend
        logger.error(f"Validation error in upload_msds_pdf: {str(ve)}", exc_info=True)
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logger.error(f"Error in upload_msds_pdf endpoint: {str(e)}", exc_info=True)
        return jsonify({"error": f"Failed to process PDF: {str(e)}. Please try another file or format. Check server logs for details."}), 500

# Entry point for running the Flask app
if __name__ == "__main__":
    # Get host and port from environment variables or use defaults
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", 5000))

    logger.info("Starting Flask development server...")
    # debug=True enables reloader and debugger. For production, set debug=False.
    # use_reloader=False is set temporarily to avoid double loading data during development
    # (Flask's reloader spawns a sub-process which reloads the app).
    # For production, you typically manage processes with Gunicorn/Waitress.
    app.run(host=host, port=port, debug=True, use_reloader=False)
# ChemSure GADSL Substance Search Tool

## 📄 Project Overview

The **ChemSure GADSL Substance Search Tool** is a web-based application designed to help users quickly search and retrieve information about substances listed in the Global Automotive Declarable Substance List (GADSL). This tool streamlines the process of checking substances against GADSL requirements, providing details on classification, reason codes, and regulatory status. It supports searching by CAS Registry Number (CAS RN), substance name, and even analyzing uploaded Material Safety Data Sheet (MSDS) PDF documents.

## ✨ Features

* **Search by CAS RN:** Quickly look up GADSL information using a Chemical Abstracts Service Registry Number.
* **Search by Substance Name:** Find GADSL details by entering the substance's common name.
* **MSDS PDF Analysis:** Upload an MSDS PDF document to automatically extract and search for listed substances within the GADSL database. (Requires a backend with PDF parsing capabilities).
* **Detailed Results:** Displays comprehensive information for found substances, including classification (Prohibited, Declarable, For Information), reason codes (Legally Regulated, For Assessment, For Information), source, reporting threshold, and more.
* **Clear All Functionality:** Easily clear all search inputs and results to start a new query.
* **User-Friendly Interface:** Intuitive and responsive design for easy navigation and use.

## 🛠️ Technologies Used

* **Frontend:**
    * HTML5 (Structure)
    * CSS3 (Styling)
    * JavaScript (Dynamic functionality, API calls)
* **Backend (Required but not included in this repository):**
    * A server-side application (e.g., Python Flask/Django, Node.js Express, etc.) is necessary to:
        * Handle API requests for CAS RN and Substance Name lookups (e.g., connecting to a GADSL database or external API).
        * Implement PDF parsing for MSDS uploads (e.g., using libraries like `PyPDF2`, `pdfminer.six` in Python, or similar in other languages).
        * Serve the `index.html`, `style.css`, and `script.js` files.

## 🚀 Getting Started

To get this project up and running locally, you will need to set up both the frontend and a compatible backend.

### Prerequisites

* A modern web browser (e.g., Chrome, Firefox, Edge).
* [Node.js](https://nodejs.org/) (if using Node.js for backend) or [Python](https://www.python.org/downloads/) (if using Flask/Django for backend).
* Git (for cloning the repository).

### Installation (Frontend Only)

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd chemsure-gadsl-search
    ```
    (Replace `<your-repository-url>` with the actual URL of your GitHub repository.)

2.  **Open in browser:**
    Simply open the `index.html` file in your web browser.
    ```bash
    # On most systems, you can just type:
    open index.html
    # Or navigate to the file in your file explorer and double-click it.
    ```
    **Note:** The search functionalities (CAS, Name, PDF) will **not work** without a running backend server that exposes the `/lookup_by_cas_rn`, `/lookup_by_substance_name`, and `/upload_msds_pdf` endpoints.

### Backend Setup (Example - Needs to be developed by you)

This frontend is designed to interact with a backend server. You will need to implement a backend that provides the following API endpoints:

* `POST /lookup_by_cas_rn`: Accepts `{"cas_rn": "..."}` and returns GADSL data.
* `POST /lookup_by_substance_name`: Accepts `{"substance_name": "..."}` and returns GADSL data.
* `POST /upload_msds_pdf`: Accepts a `multipart/form-data` containing the PDF file and returns GADSL data found within the PDF.

**Example (Conceptual Python Flask Backend):**

```python
# app.py (Example Flask structure)
from flask import Flask, request, jsonify, send_from_directory
import os
# Assume you have a GADSL_DATABASE (e.g., a list of dicts, or connected to a real DB)
# and a pdf_parser module
from .gadsl_data import GADSL_DATABASE # You need to create this
from .pdf_parser import parse_pdf_for_substances # You need to create this

app = Flask(__name__, static_folder='.') # Serve static files from current directory

# Serve frontend files
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/style.css')
def serve_css():
    return send_from_directory('.', 'style.css')

@app.route('/script.js')
def serve_js():
    return send_from_directory('.', 'script.js')

@app.route('/lookup_by_cas_rn', methods=['POST'])
def lookup_by_cas_rn():
    data = request.get_json()
    cas_rn = data.get('cas_rn')
    if not cas_rn:
        return jsonify({"error": "CAS RN is required"}), 400

    results = [item for item in GADSL_DATABASE if item.get('cas_rn') == cas_rn]
    return jsonify({"results": results})

@app.route('/lookup_by_substance_name', methods=['POST'])
def lookup_by_substance_name():
    data = request.get_json()
    substance_name = data.get('substance_name')
    if not substance_name:
        return jsonify({"error": "Substance name is required"}), 400

    results = [item for item in GADSL_DATABASE if substance_name.lower() in item.get('substance_name', '').lower()]
    return jsonify({"results": results})

@app.route('/upload_msds_pdf', methods=['POST'])
def upload_msds_pdf():
    if 'msds_pdf' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['msds_pdf']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file and file.filename.endswith('.pdf'):
        # Save the file temporarily or process directly from stream
        file_path = os.path.join('/tmp', file.filename) # Use a secure temp directory
        file.save(file_path)
        
        # Parse PDF and lookup substances
        found_substances = parse_pdf_for_substances(file_path) # Your function
        
        # Lookup against GADSL database
        gadsl_results = []
        for sub_name, cas_rn in found_substances:
            # Implement your logic to search GADSL_DATABASE for these
            # This is a simplification; you'd likely refine it
            matching_items = [item for item in GADSL_DATABASE if item.get('cas_rn') == cas_rn or sub_name.lower() in item.get('substance_name', '').lower()]
            gadsl_results.extend(matching_items)
            
        os.remove(file_path) # Clean up temp file
        return jsonify({"results": gadsl_results})
    return jsonify({"error": "Invalid file format"}), 400

if __name__ == '__main__':
    app.run(debug=True) # Run in debug mode for development

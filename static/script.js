document.addEventListener("DOMContentLoaded", () => {
    // Get references to DOM elements
    const searchForm = document.getElementById("searchForm");
    const searchResultsDiv = document.getElementById("searchResults");
    const errorMessageDiv = document.getElementById("errorMessage");
    const msdsPdfFile = document.getElementById("msdsPdfFile");
    const uploadPdfButton = document.getElementById("uploadPdfButton");
    const clearSearchButton = document.getElementById("clearSearchButton");
    const progressBar = document.getElementById("uploadProgress");

    // Initial clear of results on page load
    clearAllSearchElements();

    // Helper function to clear error messages
    function clearErrorMessage() {
        errorMessageDiv.textContent = "";
        errorMessageDiv.style.display = "none";
    }

    // Helper function to show error messages
    function showErrorMessage(message) {
        errorMessageDiv.textContent = message;
        errorMessageDiv.style.display = "block";
        searchResultsDiv.innerHTML = ""; // Clear results when showing an error
        console.error("Error displayed to user:", message);
    }

    // Helper function to clear all search fields and results area
    function clearAllSearchElements() {
        document.getElementById("casRn").value = "";
        document.getElementById("substanceName").value = "";
        if (msdsPdfFile) { 
            msdsPdfFile.value = ""; // Clears the selected file
        }
        // Set initial placeholder message for search results
        searchResultsDiv.innerHTML = `
            <div class="result-item initial-placeholder">
                <p>No results yet. Perform a search or upload a PDF.</p>
            </div>
        `;
        clearErrorMessage();
        progressBar.style.display = "none"; // Ensure progress bar is hidden on clear
        console.log("All inputs and results cleared.");
    }

    // Event listener for CAS/Substance search form submission
    if (searchForm) {
        searchForm.addEventListener("submit", async (event) => {
            event.preventDefault(); // Prevent default form submission (page reload)
            clearErrorMessage();
            searchResultsDiv.innerHTML = ""; // Clear previous results
            progressBar.style.display = "block"; // Show progress indicator for all searches

            console.log("Search form submitted.");
            const submitterId = event.submitter ? event.submitter.id : null;
            console.log("Submitted by button ID:", submitterId);

            let endpoint = "";
            let payload = {};

            if (submitterId === "searchCasButton") {
                const casNumber = document.getElementById("casRn").value.trim();
                if (!casNumber) {
                    showErrorMessage("Please enter a CAS Number.");
                    progressBar.style.display = "none";
                    return;
                }
                endpoint = "/lookup_by_cas_rn";
                payload = { cas_rn: casNumber };
            } else if (submitterId === "searchNameButton") {
                const substanceName = document.getElementById("substanceName").value.trim();
                if (!substanceName) {
                    showErrorMessage("Please enter a Substance Name.");
                    progressBar.style.display = "none";
                    return;
                }
                endpoint = "/lookup_by_substance_name";
                payload = { substance_name: substanceName };
            } else {
                showErrorMessage("Invalid search action.");
                progressBar.style.display = "none";
                return;
            }

            try {
                const response = await fetch(endpoint, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });

                console.log("Fetch response status:", response.status, response.statusText);

                if (!response.ok) {
                    const errorData = await response.json();
                    showErrorMessage(errorData.error || `Error: ${response.status} ${response.statusText}`);
                    throw new Error(`HTTP error! status: ${response.status}, message: ${JSON.stringify(errorData)}`);
                }

                const data = await response.json();
                console.log("Received data from backend:", data);

                // Assuming data.results is always an array now
                if (data.results && data.results.length > 0) {
                    displayResults(data.results);
                } else {
                    // Custom "Substance Not Found" message
                    searchResultsDiv.innerHTML = `
                        <div class="not-listed-message">
                            <h3>Substance Not Listed in GADSL</h3>
                            <p>If a substance is not listed in GADSL, it generally means:</p>
                            <ul>
                                <li><strong>Not a Known Concern:</strong> It isn't classified as regulated, restricted, or declarable.</li>
                                <li><strong>No Compliance Requirement:</strong> No legal or voluntary reporting obligations apply.</li>
                                <li><strong>New or Unclassified:</strong> It may be newly introduced or not yet reviewed.</li>
                                <li><strong>Application-Specific:</strong> Its use in automotive products doesn’t pose a known risk.</li>
                            </ul>
                            <p><strong>However, absence from GADSL doesn’t guarantee safety or unrestricted use. Manufacturers should still check local regulations (REACH, TSCA), environmental impact, and occupational health risks.</strong></p>
                        </div>
                    `;
                }
            } catch (error) {
                console.error("Error during fetch:", error);
                // If showErrorMessage was already called by response.ok check, don't overwrite
                if (!errorMessageDiv.textContent) { 
                    showErrorMessage("An error occurred while searching. Check console logs for details.");
                }
            } finally {
                progressBar.style.display = "none"; // Hide progress indicator regardless of success/failure
            }
        });
    } else {
        console.error("Search form with ID 'searchForm' not found. Check index.html.");
    }

    // Event listener for PDF upload button click
    if (uploadPdfButton) {
        uploadPdfButton.addEventListener("click", async () => {
            clearErrorMessage();
            searchResultsDiv.innerHTML = ""; // Clear previous results

            const file = msdsPdfFile.files[0];
            if (!file) {
                showErrorMessage("Please select a PDF file.");
                return;
            }

            if (file.type !== "application/pdf") {
                showErrorMessage("Upload a valid PDF file.");
                return;
            }

            const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5 MB
            if (file.size > MAX_FILE_SIZE) {
                showErrorMessage(`File size exceeds ${MAX_FILE_SIZE / (1024 * 1024)}MB. Please upload a smaller file.`);
                return;
            }

            const formData = new FormData();
            formData.append("msds_pdf", file);

            progressBar.style.display = "block"; // Show progress indicator

            try {
                const response = await fetch("/upload_msds_pdf", {
                    method: "POST",
                    body: formData, // FormData automatically sets Content-Type header
                });

                console.log("PDF Upload response status:", response.status, response.statusText);

                if (!response.ok) {
                    const errorData = await response.json();
                    showErrorMessage(errorData.error || `Error: ${response.status} ${response.statusText}`);
                    throw new Error(`HTTP error! status: ${response.status}, message: ${JSON.stringify(errorData)}`);
                }

                const data = await response.json();
                console.log("Received PDF results:", data);

                // Assuming data.results is always an array now
                if (data.results && data.results.length > 0) {
                    displayResults(data.results);
                } else {
                    searchResultsDiv.innerHTML = `
                        <div class="not-listed-message">
                            <h3>No GADSL Substances Found in PDF</h3>
                            <p>Our analysis of the uploaded PDF did not identify any substances listed in the Global Automotive Declarable Substance List (GADSL).</p>
                            <ul>
                                <li>This might be due to the PDF format (e.g., poor scan quality or image-based content).</li>
                                <li>The substances in your document might genuinely not be present in the current GADSL.</li>
                                <li>Always cross-check manually with the official GADSL if in doubt.</li>
                            </ul>
                        </div>
                    `;
                }
            } catch (error) {
                console.error("Error during PDF upload:", error);
                if (!errorMessageDiv.textContent) {
                    showErrorMessage("An error occurred during PDF processing. Check console logs.");
                }
            } finally {
                progressBar.style.display = "none"; // Ensure progress indicator is hidden on error/success
            }
        });
    } else {
        console.error("Upload button with ID 'uploadPdfButton' not found. Check index.html.");
    }

    // Event listener for Clear Search button
    if (clearSearchButton) {
        clearSearchButton.addEventListener("click", clearAllSearchElements);
    } else {
        console.error("Clear Search Button not found. Check index.html.");
    }

    // Function to display results in the searchResultsDiv
    function displayResults(results) {
        console.log("Raw results received for display:", results); // Debugging log

        searchResultsDiv.innerHTML = ""; // Clear existing results

        if (!results || results.length === 0) {
            searchResultsDiv.innerHTML = "<p>No GADSL substance found.</p>";
            return;
        }

        results.forEach(result => {
            const resultItem = document.createElement("div");
            resultItem.classList.add("result-item");

            const substanceNameForSummary = result.substance_name || 'N/A';
            const casRnForSummary = result.cas_rn || 'N/A';
            const classification = result.classification ? result.classification.trim() : '';
            
            // Ensure reason_code is uppercase, split, and sorted for consistent matching
            const rawReasonCode = result.reason_code ? result.reason_code.toUpperCase().trim() : '';
            const reasonCodesArray = rawReasonCode.split('/').map(rc => rc.trim()).filter(rc => rc !== ''); // Filter out empty strings
            const sortedReasonCodeString = reasonCodesArray.sort().join('&'); // e.g., "FA&LR" or "FI&FA&LR"

            let classificationSummaryContent = '';
            let isCustomSummaryGenerated = false;

            // --- Construct summary based on classification and sorted reason code string ---
            if (classification === 'D/P') {
                isCustomSummaryGenerated = true;
                if (sortedReasonCodeString === 'FA&FI&LR') { // D/P&FI/FA/LR
                    classificationSummaryContent = `<strong>Summary:</strong><br>${substanceNameForSummary} (CAS RN: ${casRnForSummary}) is classified as Declarable/Prohibited (D/P). The substance has mixed classification, meaning it can be declared or prohibited depending on the application. It is tracked for information, legally regulated, and under assessment. Must be declared if present above 0.1%.`;
                } else if (sortedReasonCodeString === 'FA&LR') { // D/P&FA/LR
                    classificationSummaryContent = `<strong>Summary:</strong><br>${substanceNameForSummary} (CAS RN: ${casRnForSummary}) is classified as Declarable/Prohibited (D/P). Declared or prohibited, under assessment and legally restricted. Must be declared if present above 0.1%.`;
                } else if (sortedReasonCodeString === 'FI&LR') { // D/P&FI/LR
                    classificationSummaryContent = `<strong>Summary:</strong><br>${substanceNameForSummary} (CAS RN: ${casRnForSummary}) is classified as Declarable/Prohibited (D/P). Both declarable and prohibited, tracked for information and legally regulated. Must be declared if present above 0.1%.`;
                } else if (sortedReasonCodeString === 'FA') { // D/P&FA
                    classificationSummaryContent = `<strong>Summary:</strong><br>${substanceNameForSummary} (CAS RN: ${casRnForSummary}) is classified as Declarable/Prohibited (D/P). Either declarable or prohibited, with ongoing assessment for stricter regulation. Must be declared if present above 0.1%.`;
                } else if (sortedReasonCodeString === 'LR') { // D/P&LR
                    classificationSummaryContent = `<strong>Summary:</strong><br>${substanceNameForSummary} (CAS RN: ${casRnForSummary}) is classified as Declarable/Prohibited (D/P). The substance has both allowed and prohibited uses, requiring careful evaluation. It is also legally regulated. Must be declared if present above 0.1%.`;
                } else {
                    // Default D/P summary if no specific reason code combination matches
                    classificationSummaryContent = `<strong>Summary:</strong><br>${substanceNameForSummary} (CAS RN: ${casRnForSummary}) is classified as Declarable/Prohibited (D/P). This substance has both allowed and prohibited uses in at least one region/market. Evaluate the substance entry to determine if individual substances are declarable or prohibited. Must be declared if present above 0.1%.`;
                }

            } else if (classification === 'P') {
                isCustomSummaryGenerated = true;
                if (sortedReasonCodeString === 'LR') { // P&LR
                    classificationSummaryContent = `<strong>Summary:</strong><br>${substanceNameForSummary} (CAS RN: ${casRnForSummary}) is classified as Prohibited, meaning it is banned for automotive use in at least one region or market. Legally Regulated status, indicating restrictions due to health and environmental risks.`;
                } else if (sortedReasonCodeString === 'FA') { // P&FA
                    classificationSummaryContent = `<strong>Summary:</strong><br>${substanceNameForSummary} (CAS RN: ${casRnForSummary}) is classified as Prohibited, meaning it is banned for automotive use in at least one region or market. It is also For Assessment (FA), meaning it is under review for possible regulation adjustments.`;
                } else {
                    // Default P summary if no specific reason code combination matches
                    classificationSummaryContent = `<strong>Summary:</strong><br>${substanceNameForSummary} (CAS RN: ${casRnForSummary}) is classified as Prohibited, meaning it is banned for automotive use in at least one region or market.`;
                }

            } else if (classification === 'D') {
                isCustomSummaryGenerated = true;
                if (sortedReasonCodeString === 'FA&FI&LR') { // D&FI/FA/LR
                    classificationSummaryContent = `<strong>Summary:</strong><br>${substanceNameForSummary} (CAS RN: ${casRnForSummary}) is classified as Declarable (D). Declared, tracked for information, legally regulated, and under assessment. Must be declared if it exceeds defined threshold limits.`;
                } else if (sortedReasonCodeString === 'FA&FI') { // D&FI/FA
                    classificationSummaryContent = `<strong>Summary:</strong><br>${substanceNameForSummary} (CAS RN: ${casRnForSummary}) is classified as Declarable (D). Declared for information, but also under assessment for regulation. Must be declared if it exceeds defined threshold limits.`;
                } else if (sortedReasonCodeString === 'FI&LR') { // D&FI/LR
                    classificationSummaryContent = `<strong>Summary:</strong><br>${substanceNameForSummary} (CAS RN: ${casRnForSummary}) is classified as Declarable (D). Declared for information and legally regulated in at least one market. Must be declared if it exceeds defined threshold limits.`;
                } else if (sortedReasonCodeString === 'FA&LR') { // D&FA/LR
                    classificationSummaryContent = `<strong>Summary:</strong><br>${substanceNameForSummary} (CAS RN: ${casRnForSummary}) is classified as Declarable (D). Declared, legally regulated, and under assessment for stricter control. Must be declared if it exceeds defined threshold limits.`;
                } else if (sortedReasonCodeString === 'FA') { // D&FA
                    classificationSummaryContent = `<strong>Summary:</strong><br>${substanceNameForSummary} (CAS RN: ${casRnForSummary}) is classified as Declarable (D). Must be declared and is under review for potential future regulation. Must be declared if it exceeds defined threshold limits.`;
                } else if (sortedReasonCodeString === 'LR') { // D&LR
                    classificationSummaryContent = `<strong>Summary:</strong><br>${substanceNameForSummary} (CAS RN: ${casRnForSummary}) is classified as Declarable (D). Must be declared and is legally restricted due to environmental or health risks. Must be declared if it exceeds defined threshold limits.`;
                } else if (sortedReasonCodeString === 'FI') { // D&FI
                    classificationSummaryContent = `<strong>Summary:</strong><br>${substanceNameForSummary} (CAS RN: ${casRnForSummary}) is classified as Declarable (D). Must be declared if above threshold but tracked only for information, without current regulatory restrictions. Must be declared if it exceeds defined threshold limits.`;
                } else {
                    // Default D summary if no specific reason code combination matches
                    classificationSummaryContent = `<strong>Summary:</strong><br>${substanceNameForSummary} (CAS RN: ${casRnForSummary}) is classified as Declarable (D). This substance must be declared if it exceeds defined threshold limits.`;
                }

            } else if (classification === 'FI') { // Standalone FI (without D, P, D/P)
                isCustomSummaryGenerated = true;
                classificationSummaryContent = `<strong>Summary:</strong><br>${substanceNameForSummary} (CAS RN: ${casRnForSummary}) is classified as For Information (FI). This substance is tracked for informational purposes; no current regulatory prohibition or de-selection based solely on GADSL listing.`;
            }
            // Fallback for classifications not explicitly handled above
            else {
                classificationSummaryContent = `<strong>Summary:</strong><br>${substanceNameForSummary} (CAS RN: ${casRnForSummary}) is classified as ${classification || 'N/A'}. Reason Code: ${rawReasonCode || 'N/A'}. (Definition not explicitly available in this tool. Refer to official GADSL documentation.)`;
                // For fallback, we explicitly set this to false so raw Classification/Reason Code details are shown below.
                isCustomSummaryGenerated = false; 
            }

            // Assemble the full concise summary for the substance (this is the summary box)
            const fullSummaryBoxHtml = `
                <div class="summary-box">
                    ${classificationSummaryContent}
                </div>
            `;
            resultItem.insertAdjacentHTML('afterbegin', fullSummaryBoxHtml);

            // Define the order and labels for display for *other* details
            const displayOrderForDetails = [
                { key: "substance_name", label: "Substance Name" },
                { key: "cas_rn", label: "CAS RN" },
                { key: "source", label: "Source" },
                { key: "reporting_threshold", label: "Reporting Threshold" },
                { key: "first_added", label: "First Added" },
                { key: "last_revised", label: "Last Revised" },
                { key: "generic_examples", label: "Generic Examples" }
            ];

            // Filter out 'classification' and 'reason_code' from the detailed list
            // if a custom, comprehensive summary was generated (isCustomSummaryGenerated is true).
            const filteredDisplayOrder = displayOrderForDetails.filter(item => {
                // If a specific, comprehensive summary was created for this substance,
                // we assume it already covers Classification and Reason Code.
                if (isCustomSummaryGenerated && (item.key === 'classification' || item.key === 'reason_code')) {
                    return false;
                }
                return true;
            });

            // If no custom summary was generated (meaning the fallback was used),
            // then we explicitly add the raw Classification and Reason Code for details.
            // This also ensures that if a classification like 'FI' has reason codes 'LR', 'FA', etc.,
            // those reason codes would still be displayed as separate lines if `isCustomSummaryGenerated`
            // is not true for that specific combination.
            if (!isCustomSummaryGenerated) {
                resultItem.appendChild(createDetailElement("Classification", classification || 'N/A'));
                resultItem.appendChild(createDetailElement("Reason Code", rawReasonCode || 'N/A'));
            }

            // Append each remaining detail to the result item based on filtered list
            filteredDisplayOrder.forEach(item => {
                let value = result[item.key] ?? "N/A";
                
                // Specific handling for Reporting Threshold
                if (item.key === "reporting_threshold" && (value === "N/A" || value.trim() === '')) {
                    value = "0.1%"; // Default threshold
                }
                resultItem.appendChild(createDetailElement(item.label, value));
            });
            
            searchResultsDiv.appendChild(resultItem);
            searchResultsDiv.appendChild(document.createElement("hr")); // Separator
        });
    }

    // Helper function to create a detail paragraph element
    function createDetailElement(label, value) {
        const p = document.createElement("p");
        p.innerHTML = `<strong>${label}:</strong> ${value}`;
        return p;
    }
});

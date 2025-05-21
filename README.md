# Gemini Web Script

This script uses Playwright to fetch web content and lxml to parse the HTML. It can find and suggest text replacements on a webpage.

## Prerequisites

- Python 3.12
- Playwright

## Setup

1.  **Clone the repository:**
    ```bash
    git clone git@github.com:sachitshivam/dom-text-replacer-fibr.git
    cd dom-text-replacer-fibr
    # Navigate to the directory containing the scripts.
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install Playwright browsers:**
    The first time you run Playwright, or if the necessary browser binaries are missing, Playwright will download them. You can also install them manually:
    ```bash
    playwright install
    ```
    This command installs the default browsers (Chromium, Firefox, WebKit). If you only need a specific browser (e.g., Chromium, which is used by default in the script), you can specify it:
    ```bash
    playwright install chromium
    ```

## Running the Script

The main script to run is `test_scenario_runner.py`. It uses `dom_text_replacer.py` to perform the text replacement logic.

To run the example scenario:
```bash
python gemini_web_script/test_scenario_runner.py
```

The script will:
1.  Fetch the content from the URL specified in `test_scenario_runner.py` (e.g., `https://fibr.ai/`).
2.  Process the predefined suggestions for text changes.
3.  Print the results, including a change log with XPaths and proposed text modifications, in JSON format.

## How it Works

-   **`dom_text_replacer.py`**:
    -   `DomTextReplacer` class:
        -   `_fetch_content(url)`: Fetches the webpage content using Playwright.
        -   `_normalize_text(text)`: Cleans and standardizes text (unescapes HTML, collapses whitespace).
        -   `_get_element_xpath(element)`: Generates an XPath for a given lxml HTML element.
        -   `_extract_text_segments_with_parents()`: Extracts all text nodes from the HTML body, along with their parent elements, filtering out non-content tags (like `<script>`, `<style>`).
        -   `_distribute_new_val(new_val_str, current_texts_in_match)`: Proportionally distributes words from a new string to a list of current text segments based on their original word counts. This is used when a matched text spans multiple HTML text nodes.
        -   `find_and_prepare_changes(url, suggestions)`: The main method. It takes a URL and a list of suggestions (each a dictionary with `current_val` and `new_val`). It iterates through the extracted text segments, tries to find matches for `current_val`, and if found, prepares a change log detailing the XPath of the element, the original text segment, and the proposed new text segment (distributed if necessary).

-   **`test_scenario_runner.py`**:
    -   An example script that demonstrates how to use the `DomTextReplacer`.
    -   It defines a URL and a list of text replacement suggestions.
    -   It instantiates `DomTextReplacer`, calls `find_and_prepare_changes`, and prints the JSON output.

## Customization

To use this for your own purposes:

1.  **Modify `test_scenario_runner.py`**:
    -   Change the `url_fibr` variable to the URL of the website you want to process.
    -   Update the `suggestions_fibr` list with your desired `current_val` (text to find) and `new_val` (text to replace with).
2.  **Run the script**: `python gemini_web_script/test_scenario_runner.py`
3.  **Review the output**: The JSON output will provide the `change_log` for each suggestion, indicating where the text was found (via XPath) and what the new text would be.

This script focuses on identifying and preparing changes. Applying these changes directly to a live website or HTML file would require additional logic (e.g., using Playwright to execute JavaScript to modify the DOM, or lxml to rewrite the HTML structure).
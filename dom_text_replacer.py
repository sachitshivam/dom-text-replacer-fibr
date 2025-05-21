import html as html_parser  # for unescape
import json
import re

from lxml import html as lxml_html
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright


class DomTextReplacer:
    """
    A utility to identify DOM elements for text replacement suggestions on a live webpage,
    providing granular change logs for text segments.
    """

    def __init__(self):
        # Initialize the DOM tree, body, raw HTML content, and a cache for extracted text data
        self.tree = None
        self.body = None
        self.raw_content = None
        # Cache for (parent_element_of_text_node, original_text_node_content, normalized_text_node_content)
        self.elements_data_cache = []

    def _fetch_content(self, url: str):
        """Fetches HTML content from the URL using Playwright."""
        print(f"Fetching content from: {url}")
        try:
            # Launch a headless browser and navigate to the URL
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(url, timeout=90000, wait_until="networkidle")
                self.raw_content = page.content()  # Get the full HTML content
                browser.close()
            if not self.raw_content:
                raise ValueError("Failed to fetch content (empty response).")
            # Parse the HTML content into an lxml tree
            self.tree = lxml_html.fromstring(self.raw_content)
            self.body = self.tree.find(".//body")
            if self.body is None:
                # Fallback: try to find the <html> tag if <body> is missing
                self.body = self.tree.find(".//html")
                if self.body is None:
                    raise ValueError("HTML body or html tag not found in the document.")
            print("Content fetched and parsed successfully.")
        except PlaywrightError as e:
            print(f"Playwright error fetching URL {url}: {e}")
            raise
        except Exception as e:
            print(f"Error fetching or parsing URL {url}: {e}")
            raise

    def _normalize_text(self, text: str) -> str:
        """Normalizes text by unescaping HTML, collapsing whitespace, and stripping."""
        if text is None:
            return ""
        try:
            text = html_parser.unescape(text)
        except TypeError:
            return ""
        text = re.sub(r"\s+", " ", text)  # Collapse all whitespace to single spaces
        return text.strip()  # Remove leading/trailing whitespace

    def _get_element_xpath(self, element) -> str:
        """Generates the XPath for a given lxml element."""
        if element is None:
            return "XPATH_ERROR_NO_ELEMENT_PROVIDED"
        try:
            tree = element.getroottree()
            if tree is None:
                return "XPATH_ERROR_ELEMENT_NOT_IN_TREE"
            return tree.getpath(element)  # Get the XPath string for the element
        except Exception as e:
            print(f"Could not generate XPath for element due to exception: {e}")
            return "XPATH_ERROR_EXCEPTION_OCCURRED"

    def _extract_text_segments_with_parents(self):
        """
        Extracts text segments (from text nodes) and their direct parent elements.
        Filters out text from non-visible/non-content tags based on parent.
        Stores (parent_element, original_text_node_content, normalized_text_node_content).
        """
        if self.body is None:
            self.elements_data_cache = []
            return

        print("Extracting text segments with their parent elements...")
        extracted_data = []
        # Iterate over all text nodes within the body in document order
        for text_node_obj in self.body.xpath(".//text()"):
            parent_element = text_node_obj.getparent()
            if parent_element is None:
                continue  # Should be rare, skip if text node has no parent

            # Filter out text nodes whose PARENT is a non-content tag
            parent_tag_name = parent_element.tag
            if isinstance(parent_tag_name, str):  # Lxml elements have string tags
                parent_tag_name = parent_tag_name.lower()
                if parent_tag_name in [
                    "script",
                    "style",
                    "noscript",
                    "title",
                    "meta",
                    "link",
                    "head",
                ]:
                    continue  # Skip non-content tags
            # else: if tag is not a string (e.g. a Comment or PI), it won't be in the set, which is fine.

            original_text_content = str(text_node_obj)  # Get the actual text of this text node
            normalized_text_content = self._normalize_text(original_text_content)

            if normalized_text_content:  # Only consider if it has some text after normalization
                extracted_data.append(
                    (parent_element, original_text_content, normalized_text_content)
                )

        self.elements_data_cache = extracted_data
        print(f"Extracted {len(self.elements_data_cache)} text segments with parent elements.")

    def _distribute_new_val(
        self, new_val_str: str, current_texts_in_match: list[str]
    ) -> list[str]:
        """Distributes words from new_val_str proportionally to current_texts_in_match word counts."""
        # Normalize and split the new value into words
        new_words = self._normalize_text(new_val_str).split()
        total_new_words_count = len(new_words)

        # Handle edge cases: no segments to distribute to, or no new words
        if not current_texts_in_match:
            return []
        if total_new_words_count == 0:
            return [""] * len(current_texts_in_match)

        # Count words in each current text segment
        current_word_counts = [
            len(self._normalize_text(s).split()) for s in current_texts_in_match
        ]
        total_current_words = sum(current_word_counts)

        # Prepare lists to hold the assigned text and word counts for each segment
        assigned_texts = [""] * len(current_texts_in_match)
        assigned_word_counts = [0] * len(current_texts_in_match)

        if total_current_words > 0:
            # Distribute new words proportionally to the original word counts
            for i in range(len(current_texts_in_match)):
                proportion = current_word_counts[i] / total_current_words
                # Assign a rounded number of words to each segment based on its proportion
                assigned_word_counts[i] = round(proportion * total_new_words_count)
        else:
            # If all segments are empty, distribute new words as evenly as possible
            if len(current_texts_in_match) > 0:
                base_count = total_new_words_count // len(current_texts_in_match)
                remainder = total_new_words_count % len(current_texts_in_match)
                for i in range(len(current_texts_in_match)):
                    # Distribute the remainder one by one to the first few segments
                    assigned_word_counts[i] = base_count + (1 if i < remainder else 0)

        # Adjust for rounding errors so the total matches exactly
        current_sum_assigned = sum(assigned_word_counts)
        diff = total_new_words_count - current_sum_assigned

        idx_adj = 0
        while diff != 0:
            if not assigned_word_counts:
                break

            target_idx = idx_adj % len(assigned_word_counts)
            adjustment = 1 if diff > 0 else -1

            # Only adjust if the result will not be negative
            if assigned_word_counts[target_idx] + adjustment >= 0:
                assigned_word_counts[target_idx] += adjustment
                diff -= adjustment

            idx_adj += 1
            # Safety: avoid infinite loop
            if idx_adj > 2 * (total_new_words_count + len(assigned_word_counts)):
                final_re_sum = sum(assigned_word_counts)
                final_diff = total_new_words_count - final_re_sum
                if final_diff != 0 and assigned_word_counts:
                    assigned_word_counts[-1] += final_diff
                    if assigned_word_counts[-1] < 0:
                        assigned_word_counts[-1] = 0
                break

        # Now, assign the actual words to each segment based on the assigned word counts
        word_idx = 0
        for i in range(len(current_texts_in_match)):
            num_to_take = max(0, assigned_word_counts[i])
            end_word_idx = min(word_idx + num_to_take, total_new_words_count)
            # Join the assigned words for this segment
            assigned_texts[i] = " ".join(new_words[word_idx:end_word_idx])
            word_idx = end_word_idx

        # If any words remain (due to rounding), append them to the last segment
        if word_idx < total_new_words_count and assigned_texts:
            remaining_text = " ".join(new_words[word_idx:])
            assigned_texts[-1] = (assigned_texts[-1] + " " + remaining_text).strip()

        return assigned_texts

    def find_and_prepare_changes(self, url: str, suggestions: list[dict]) -> list[dict]:
        """
        Main method to find text occurrences and prepare change logs.
        Given a URL and a list of suggestions (each with 'current_val' and 'new_val'),
        it fetches the page, extracts text segments, finds matches, and prepares a change log
        with the XPath and text for each segment to be replaced.
        """
        self._fetch_content(url)
        # Call the new data extraction method
        self._extract_text_segments_with_parents()

        results = []

        for suggestion_idx, suggestion in enumerate(suggestions):
            current_val_orig = suggestion["current_val"]
            new_val_orig = suggestion["new_val"]
            target_search_text = self._normalize_text(current_val_orig)

            print(
                f"\nProcessing suggestion {suggestion_idx+1}: '{current_val_orig}' ->"
                f" '{new_val_orig}'"
            )

            output_item = {
                "current_val": current_val_orig,
                "new_val": new_val_orig,
                "change_log": [],
            }

            if not target_search_text:
                print(
                    f"Skipping suggestion for empty/whitespace current_val: '{current_val_orig}'"
                )
                results.append(output_item)
                continue

            match_found_for_this_suggestion = False
            # self.elements_data_cache now contains (parent_element, text_node_content, normalized_text_node_content)
            for i in range(len(self.elements_data_cache)):
                # current_sequence_details stores (parent_element, original_text_node_content)
                current_sequence_details = []
                current_normalized_texts_in_sequence = []

                for j in range(i, len(self.elements_data_cache)):
                    # element_j is the parent_element of the text node
                    # original_text_j is the original_text_node_content
                    # normalized_text_j is the normalized_text_node_content
                    element_j, original_text_j, normalized_text_j = self.elements_data_cache[j]

                    # normalized_text_j is guaranteed non-empty by _extract_text_segments_with_parents
                    potential_normalized_texts = current_normalized_texts_in_sequence + [
                        normalized_text_j
                    ]
                    concatenated_normalized_text = self._normalize_text(
                        " ".join(potential_normalized_texts)
                    )

                    if concatenated_normalized_text == target_search_text:
                        # Found a full match for the suggestion
                        current_sequence_details.append((element_j, original_text_j))

                        change_log_entries = []
                        original_texts_for_distribution = []

                        for matched_elem, matched_orig_text_segment in current_sequence_details:
                            change_log_entries.append({
                                "xPath": self._get_element_xpath(matched_elem),
                                "current_text": (
                                    matched_orig_text_segment  # This is now the specific text node's content
                                ),
                            })
                            original_texts_for_distribution.append(matched_orig_text_segment)

                        # Distribute the new value's words across the matched segments
                        distributed_new_texts = self._distribute_new_val(
                            new_val_orig, original_texts_for_distribution
                        )

                        if len(distributed_new_texts) == len(change_log_entries):
                            for k_idx, entry in enumerate(change_log_entries):
                                entry["new_text"] = distributed_new_texts[k_idx]
                        else:
                            print(
                                "Warning: Mismatch in distributed text count for"
                                f" '{current_val_orig}'. Assigning new_val to first element if log"
                                " exists."
                            )
                            if change_log_entries:
                                change_log_entries[0]["new_text"] = new_val_orig

                        output_item["change_log"] = change_log_entries
                        match_found_for_this_suggestion = True
                        print(
                            f"Match found for '{current_val_orig}' involving"
                            f" {len(change_log_entries)} text segment(s)."
                        )
                        break

                    # Check for valid prefix (ends at space, or is the full target)
                    # normalized_text_j is guaranteed non-empty here.
                    elif (
                        target_search_text.startswith(concatenated_normalized_text)
                        and len(concatenated_normalized_text) < len(target_search_text)
                        and target_search_text[len(concatenated_normalized_text)] == " "
                    ):
                        # Continue accumulating segments for a possible match
                        current_sequence_details.append((element_j, original_text_j))
                        current_normalized_texts_in_sequence.append(normalized_text_j)
                    else:
                        # No match or valid prefix, break out of the inner loop
                        break

                if match_found_for_this_suggestion:
                    break

            results.append(output_item)
            if not match_found_for_this_suggestion:
                print(f"Warning: No full match found for current_val: '{current_val_orig}'")

        print("\nProcessing complete.")
        return results

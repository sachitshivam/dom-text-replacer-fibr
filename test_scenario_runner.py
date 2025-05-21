import json

from dom_text_replacer import DomTextReplacer

if __name__ == "__main__":
    replacer = DomTextReplacer()

    url_fibr = "https://fibr.ai/"
    suggestions_fibr = [
        {
            "current_val": "Turn Your Website Into a Smart, Self-Optimizing Growth Machine",
            "new_val": "Boost Conversions 30%+ With AI-Powered Website Optimization",
        },
        {
            "current_val": (
                "Run 100x more experiments, 10x faster with AI Agents that"
                " automate testing & personalization. No extra hires, no"
                " agencies, no new tools. Just smarter conversions, on"
                " autopilot."
            ),
            "new_val": (
                "Our AI Agents deliver 55% higher conversion rates by running"
                " 100x more experiments automatically - no extra hires,"
                " agencies, or tools needed."
            ),
        },
        {
            "current_val": "Talk to CRO Expert",
            "new_val": "Get Your CRO Analysis",
        },
    ]

    try:
        results_fibr = replacer.find_and_prepare_changes(url_fibr, suggestions_fibr)
        print("\n--- Results ---")
        print(json.dumps(results_fibr, indent=4))
    except Exception as e:
        print(f"An error occurred during processing: {e}")

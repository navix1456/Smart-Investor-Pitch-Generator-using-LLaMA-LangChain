import sys
import json
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup

def scrape_crunchbase_profile(url: str) -> dict:
    """
    Scrapes a Crunchbase profile URL and returns a dictionary of investor data.
    Saves the HTML to debug_crunchbase.html for debugging.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        content = None
        try:
            page.goto(url, timeout=30000)
            page.wait_for_selector('h1.profile-name', timeout=15000)
            content = page.content()
        except Exception as e:
            # Try to get the page content even on error
            try:
                content = page.content()
            except Exception:
                content = None
            if content:
                with open("debug_crunchbase.html", "w", encoding="utf-8") as f:
                    f.write(content)
            print(json.dumps({"error": f"Scraping failed: {repr(e)}"}), file=sys.stderr)
            sys.exit(1)
        finally:
            browser.close()

    if content:
        with open("debug_crunchbase.html", "w", encoding="utf-8") as f:
            f.write(content)

    soup = BeautifulSoup(content, "html.parser")
    
    name_tag = soup.select_one("h1.profile-name")
    name = name_tag.text.strip() if name_tag else "Investor"

    bio_tag = soup.select_one("div.description-text > span")
    bio = bio_tag.text.strip() if bio_tag else "Not specified"

    interests_tags = soup.select('a.chip')
    interests = ", ".join([tag.text.strip() for tag in interests_tags]) or "Not specified"

    return {
        "name": name,
        "bio": bio,
        "interests": interests
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No URL provided"}), file=sys.stderr)
        sys.exit(1)
    
    profile_url = sys.argv[1]
    data = scrape_crunchbase_profile(profile_url)
    print(json.dumps(data)) 
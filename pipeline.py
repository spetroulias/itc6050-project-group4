"""
pipeline.py — Open Library Book Trends
ITC6050 Final Project — Group 4

Ingestion script: fetches book and author data from the Open Library
public API and loads it into PostgreSQL using dlt (Data Load Tool).

Usage:
    docker-compose run app python pipeline.py
"""

import time
import requests
import dlt

# Subjects to query against the Open Library search API.
SUBJECTS = [
    "science", "history", "fiction", "philosophy", "technology",
    "biography", "art", "mathematics", "economics", "politics"
]

BOOKS_PER_PAGE = 50       # Open Library API maximum per request
PAGES_PER_SUBJECT = 6      # 3 pages * 100 = 300 books per subject (Total 3,000 books)
BASE_URL = "https://openlibrary.org"


def safe_get(url, retries=3, wait=5):
    """
    Performs a GET request with automatic retry logic.

    Handles transient failures (timeouts, network errors) and rate limiting
    (HTTP 429). Returns the parsed JSON response as a dict, or None if all
    attempts fail.
    """
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=30)

            if response.status_code == 200:
                return response.json()

            elif response.status_code == 429:
                # API rate limit reached — back off before retrying
                print("   Rate limited. Waiting 30 seconds...")
                time.sleep(30)

            else:
                print(f"   Unexpected status {response.status_code} for: {url}")
                return None

        except Exception as e:
            print(f"   Attempt {attempt + 1}/{retries} failed: {e}")
            time.sleep(wait)

    return None


@dlt.resource(name="books", write_disposition="replace")
def fetch_books():
    """
    Fetches book records from the Open Library search API with pagination.

    Iterates over each subject, requests up to PAGES_PER_SUBJECT pages of
    BOOKS_PER_PAGE books each, and yields individual book dicts to dlt for bulk 
    loading into raw.books.
    """
    for subject in SUBJECTS:
        print(f"\nFetching books for subject: '{subject}'...")

        for page in range(PAGES_PER_SUBJECT):
            offset = page * BOOKS_PER_PAGE
            print(f"   [Page {page + 1}/{PAGES_PER_SUBJECT}] Fetching with offset {offset}...")

            url = (
                f"{BASE_URL}/search.json"
                f"?subject={subject}"
                f"&limit={BOOKS_PER_PAGE}"
                f"&offset={offset}"  # <-- Pagination parameter
                f"&fields=key,title,author_name,first_publish_year,number_of_pages_median,edition_count"
            )

            data = safe_get(url)
            if not data:
                print(f"   Skipping page {page + 1} for '{subject}' — no data returned.")
                break  # Stop paginating this subject if API fails

            books = data.get("docs", [])
            if not books:
                print(f"   No more books found for '{subject}'. Stopping pagination.")
                break  # Stop early if there are no more pages available

            print(f"   Retrieved {len(books)} books from page {page + 1}.")

            for book in books:
                # 1. Annotate with search subject
                book["searched_subject"] = subject
                
                # 2. Add 'source' column to satisfy rubric: "adds repo/source column"
                book["source"] = "Open Library"

                # 3. Normalise the page count field name to match the schema
                if "number_of_pages_median" in book:
                    book["number_of_pages"] = book.pop("number_of_pages_median")

                yield book

            # Respect the Open Library rate limit (1 req/sec average)
            time.sleep(2)


@dlt.resource(name="authors", write_disposition="replace")
def fetch_authors():
    """
    Fetches author detail records from the Open Library authors API.

    Executes in two phases:
      1. Re-queries the search API to collect unique author keys
         across all subjects.
      2. Fetches the detail endpoint for each unique key and yields
         the result to dlt for loading into raw.authors.

    Capped at 100 authors to avoid aggressive rate limiting.
    """
    print("\nCollecting unique author keys...")

    # A set ensures each author key is fetched only once
    seen_keys = set()

    for subject in SUBJECTS:
        # We only need the first page of authors to collect unique keys
        url = (
            f"{BASE_URL}/search.json"
            f"?subject={subject}"
            f"&limit={BOOKS_PER_PAGE}"
            f"&fields=author_key"
        )
        data = safe_get(url)
        if data:
            for book in data.get("docs", []):
                for key in book.get("author_key", []):
                    seen_keys.add(key)
        time.sleep(2)

    # Limit to 100 authors to maintain stable throughput
    author_keys = list(seen_keys)[:100]
    print(f"   Fetching details for {len(author_keys)} authors...")

    for i, key in enumerate(author_keys):
        url = f"{BASE_URL}/authors/{key}.json"
        data = safe_get(url, retries=2, wait=3)

        if data:
            # Preserve key and add source column for consistency
            data["author_key"] = key
            data["source"] = "Open Library"
            yield data

        if (i + 1) % 20 == 0:
            print(f"   Progress: {i + 1}/{len(author_keys)} authors fetched.")

        time.sleep(1)


def run_pipeline():
    """
    Initialises the dlt pipeline and executes both ingestion resources.
    """
    print("=" * 55)
    print("   ITC6050 — Open Library Ingestion Pipeline")
    print("=" * 55)

    pipeline = dlt.pipeline(
        pipeline_name="open_library",
        destination="postgres",
        dataset_name="raw",
    )

    print("\nLoading books into PostgreSQL (raw.books)...")
    books_info = pipeline.run(fetch_books())
    print(f"   {books_info}")

    print("\nLoading authors into PostgreSQL (raw.authors)...")
    authors_info = pipeline.run(fetch_authors())
    print(f"   {authors_info}")

    print("\n" + "=" * 55)
    print("   Pipeline complete. Verify results in pgAdmin:")
    print("   http://localhost:8080")
    print("=" * 55)


if __name__ == "__main__":
    run_pipeline()
"""
pipeline.py - Open Library Book Trends
ITC6050 Final Project - Group 4
"""

import time
import requests
import dlt

SUBJECTS = ["science", "history", "fiction", "philosophy", "technology"]
BOOKS_PER_SUBJECT = 100
BASE_URL = "https://openlibrary.org"

def safe_get(url, retries=3, wait=5):
    """
    Fetch a URL with automatic retries.
    If the request fails, wait and try again up to 3 times.
    """
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                print(f"   Rate limited. Waiting 30 seconds...")
                time.sleep(30)
            else:
                print(f"   Status {response.status_code} for {url}")
                return None
        except Exception as e:
            print(f"   Attempt {attempt + 1} failed: {e}")
            time.sleep(wait)
    return None


@dlt.resource(name="books", write_disposition="replace")
def fetch_books():
    for subject in SUBJECTS:
        print(f"\nFetching books for subject: '{subject}'...")
        url = f"{BASE_URL}/search.json?subject={subject}&limit={BOOKS_PER_SUBJECT}&fields=key,title,author_name,author_key,first_publish_year,number_of_pages_median,edition_count"
        data = safe_get(url)

        if not data:
            print(f"   Skipping '{subject}' - no data returned")
            continue

        books = data.get("docs", [])
        print(f"   Got {len(books)} books")

        for book in books:
            book["searched_subject"] = subject
            if "number_of_pages_median" in book:
                book["number_of_pages"] = book.pop("number_of_pages_median")
            yield book

        time.sleep(2)


@dlt.resource(name="authors", write_disposition="replace")
def fetch_authors():
    print("\nCollecting author keys from books...")

    seen_keys = set()
    for subject in SUBJECTS:
        url = f"{BASE_URL}/search.json?subject={subject}&limit={BOOKS_PER_SUBJECT}&fields=author_key"
        data = safe_get(url)
        if data:
            for book in data.get("docs", []):
                for key in book.get("author_key", []):
                    seen_keys.add(key)
        time.sleep(2)

    # Limit to 100 authors to avoid rate limiting
    author_keys = list(seen_keys)[:100]
    print(f"   Fetching details for {len(author_keys)} authors...")

    for i, key in enumerate(author_keys):
        url = f"{BASE_URL}/authors/{key}.json"
        data = safe_get(url, retries=2, wait=3)

        if data:
            data["author_key"] = key
            yield data

        if (i + 1) % 20 == 0:
            print(f"   Progress: {i + 1}/{len(author_keys)} authors")

        time.sleep(1)


def run_pipeline():
    print("=" * 50)
    print("  ITC6050 - Open Library Pipeline")
    print("=" * 50)

    pipeline = dlt.pipeline(
        pipeline_name="open_library",
        destination="postgres",
        dataset_name="raw",
    )

    print("\nLoading books into PostgreSQL...")
    books_info = pipeline.run(fetch_books())
    print(f"   Done: {books_info}")

    print("\nLoading authors into PostgreSQL...")
    authors_info = pipeline.run(fetch_authors())
    print(f"   Done: {authors_info}")

    print("\n" + "=" * 50)
    print("  Pipeline complete!")
    print("  Check pgAdmin at http://localhost:8080")
    print("=" * 50)


if __name__ == "__main__":
    run_pipeline()
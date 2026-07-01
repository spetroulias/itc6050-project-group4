/*
  test_valid_publish_year.sql — Custom dbt Test
  ITC6050 Project 4

  WHAT IT CHECKS:
    No book in the staging model should have a publish year
    outside the range 1800–2024.

  HOW dbt TESTS WORK:
    If this query returns ANY rows → the test FAILS
    If this query returns 0 rows  → the test PASSES

  Run with:
    docker-compose run app dbt test --select stg_books
*/

SELECT
    book_key,
    title,
    first_publish_year
FROM {{ ref('stg_books') }}
WHERE
    first_publish_year < 1800
    OR first_publish_year > 2024

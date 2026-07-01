WITH raw_books AS (

    SELECT * FROM {{ source('raw', 'books') }}

),

cleaned AS (

    SELECT
        key                                         AS book_key,
        title,
        first_publish_year::INTEGER                 AS first_publish_year,
        (first_publish_year::INTEGER / 10) * 10     AS decade,
        searched_subject                            AS subject,
        number_of_pages::INTEGER                    AS number_of_pages,
        edition_count::INTEGER                      AS edition_count

    FROM raw_books

    WHERE
        first_publish_year IS NOT NULL
        AND first_publish_year::INTEGER BETWEEN 1900 AND 2024
        AND title IS NOT NULL
        AND key IS NOT NULL

)

SELECT * FROM cleaned

WITH staged AS (

    SELECT * FROM {{ ref('stg_books') }}

),

summary AS (

    SELECT
        subject,
        decade,
        COUNT(*)                        AS book_count,
        ROUND(AVG(number_of_pages), 0)  AS avg_pages,
        SUM(edition_count)              AS total_editions

    FROM staged

    GROUP BY subject, decade

)

SELECT
    *,
    ROUND(
        book_count * 100.0 / SUM(book_count) OVER (),
        2
    ) AS pct_of_total

FROM summary
ORDER BY subject, decade
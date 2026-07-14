with raw_books as (

    select * from {{ source('raw', 'books') }}

),

deduplicated as (

    select 
        *,
        -- Αριθμούμε τις εγγραφές για κάθε key. Η πρώτη θα πάρει το 1.
        row_number() over (
            partition by key 
            order by first_publish_year::integer desc
        ) as rn
    from raw_books

),

cleaned as (

    select
        key                                         as book_key,
        title,
        first_publish_year::integer                 as first_publish_year,
        (first_publish_year::integer / 10) * 10     as decade,
        searched_subject                            as subject,
        number_of_pages::integer                    as number_of_pages,
        edition_count::integer                      as edition_count

    from deduplicated

    where
        rn = 1 -- Κρατάμε ΜΟΝΟ τη μία μοναδική εγγραφή για κάθε key
        and first_publish_year is not null
        and first_publish_year::integer between 1900 and 2024
        and title is not null
        and key is not null

)

select * from cleaned

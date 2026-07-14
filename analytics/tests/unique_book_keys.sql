-- unique book keys

select
    book_key,
    count(*) as occurrences
from {{ ref('stg_books') }}
group by book_key
having count(*) > 1
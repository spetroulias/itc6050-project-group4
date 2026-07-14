--checking for not null values--

select *
from {{ ref('stg_books') }}
where book_key is null 
   or title is null 
   or first_publish_year is null
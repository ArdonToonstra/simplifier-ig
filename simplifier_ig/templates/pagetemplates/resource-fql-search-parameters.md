---
topic: resource-fql-search-parameters
---

### Search Parameters

<fql>
    from SearchParameter
    where base contains '%subject'
    select name, url, type, description, expression
</fql>

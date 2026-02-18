---
topic: resource-meta
---

<fql>
from StructureDefinition
where url = %canonical
select 
    Name: name,
    Description: description,
    Version: version,
    Status: status,
    Canonical: url,
    Parent: baseDefinition
</fql>

| Canonical | Parent |
|---|---|
| <fql output="inline"> from StructureDefinition where url = %canonical select url</fql> | <fql output="inline">  from StructureDefinition where url = %canonical select baseDefinition</fql> |

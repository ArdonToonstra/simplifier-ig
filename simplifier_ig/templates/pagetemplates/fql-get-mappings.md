---
topic: fql-get-mappings
---
<fql>
  from
    StructureDefinition
  where
    url=%canonical
  for
    snapshot.element 
  select
    id, join mapping {identity, map, comment}
  select identity, map, id, comment
  order by identity
</fql>
---
topic: resource-fql-terminology-bindings
---

### Terminology bindings

<fql>
    from StructureDefinition
    where url = %canonical
    select
    title,
    join differential.element.where(binding.strength.exists())
    {
        path,
        binding.strength,
        binding.valueSet
    }
    order by title
</fql>

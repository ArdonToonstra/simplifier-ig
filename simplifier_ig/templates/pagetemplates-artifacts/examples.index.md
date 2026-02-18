---
topic: examples-index
---

## {{page-title}}

<fql>
	from
		Resource
	where 
		meta.profile.empty().not()
	select
		Example: '{{pagelink:example-'+ id + '}}',
		ResourceType: typename(),
		ConformsToProfile: '{{pagelink:StructureDefinition-'+ meta.profile[0].substring(42) + '}}'
	order by Example
</fql>
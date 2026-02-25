---
topic: messagedefinition-index
---

## {{page-title}}

<fql>
	from 
		MessageDefinition
	select 
		Name: '{{pagelink:MessageDefinition-' + id + '}}',
		Description: description,
		Canonical: url
	order by 
		Name
</fql>

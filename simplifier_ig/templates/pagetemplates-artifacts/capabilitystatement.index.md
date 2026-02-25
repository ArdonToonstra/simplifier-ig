---
topic: capabilitystatement-index
---

## {{page-title}}

<fql>
	from 
		CapabilityStatement
	select 
		Name: '{{pagelink:CapabilityStatement-' + id + '}}',
		Description: description,
		Canonical: url
	order by 
		Name
</fql>

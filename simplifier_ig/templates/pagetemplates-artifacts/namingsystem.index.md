---
topic: namingsystem-index
---

## {{page-title}}

<fql>
	from 
		NamingSystem
	select 
		Name: '{{pagelink:NamingSystem-' + id + '}}',
		Description: description
	order by 
		Name
</fql>

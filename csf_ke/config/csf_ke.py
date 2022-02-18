from __future__ import unicode_literals
from frappe import _


def get_data():
	return [
		{
			"label": _("Kenya"),
			"items": [
				{
				   "description": "CSF Kenya",  
				   "label": "CSF KE",					
				   "type": "report"
				},
				{
				   "type": "report", 
				   "description": "NHIF Report", 
				   "name": "NHIF Report", 
				},
				{
				   "type": "report", 
				   "description": "HELB Report", 
				   "name": "HELB Report", 
				},
				{
				   "type": "report", 
				   "description": "NSSF Report", 
				   "name": "NSSF Report", 
				},
				{
				   "type": "report", 
				   "description": "Payroll Register", 
				   "name": "Payroll Register", 
				},
                {
                   "type": "report", 
				   "description": "Bank Payroll Advice", 
				   "name": "Bank Payroll Advice",
                },
                {
                    "type": "report", 
                    "description": "P9A Tax Deduction Card", 
                    "name": "P9A Tax Deduction Card",
                },
                {
                    "type": "report", 
                    "description": "Sales Tax Report", 
                    "name": "Sales Tax Report",
                },
                {
                    "type": "report", 
                    "description": "Purchase Tax Report", 
                    "name": "Purchase Tax Report",
                }
            ]

        }
	]
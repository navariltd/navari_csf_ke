// Copyright (c) 2025, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports['Kenya SHIF Contribution'] = {
  filters: [
    {
      fieldname: 'company',
      label: __('Company'),
      fieldtype: 'Link',
      options: 'Company',
      default: frappe.defaults.get_user_default('Company'),
      width: '100px',
      reqd: 1,
    },
    {
      fieldname: 'from_date',
      label: __('From Date'),
      fieldtype: 'Date',
      default: frappe.datetime.add_months(frappe.datetime.get_today(), -1), // Default to last month
      reqd: 1,
      width: '100px',
    },
    {
      fieldname: 'to_date',
      label: __('To Date'),
      fieldtype: 'Date',
      default: frappe.datetime.get_today(), // Default to today
      reqd: 1,
      width: '100px',
    },
    {
      fieldname: 'employee',
      label: __('Employee'),
      fieldtype: 'Link',
      options: 'Employee',
      width: '150px',
      get_query: function () {
        var company = frappe.query_report.get_filter_value('company');
        return {
          doctype: 'Employee',
          filters: {
            company: company,
          },
        };
      },
    },
  ],
};

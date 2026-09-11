// Copyright (c) 2022, Navari Limited and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Kenya Sales Tax Report"] = {
  filters: [
    {
      fieldname: "company",
      label: __("Company"),
      fieldtype: "Link",
      options: "Company",
      default: frappe.defaults.get_user_default("Company"),
      width: "100px",
      reqd: 1,
    },
    {
      fieldname: "from_date",
      label: __("Start Date"),
      fieldtype: "Date",
      default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
      reqd: 1,
      width: "100px",
    },
    {
      fieldname: "to_date",
      label: __("End Date"),
      fieldtype: "Date",
      default: frappe.datetime.get_today(),
      reqd: 1,
      width: "100px",
    },
    {
      fieldname: "is_return",
      label: __("Is Return"),
      fieldtype: "Select",
      options: ["", "Is Return", "Normal Sales Invoice"],
      default: "",
      reqd: 0,
      width: "100px",
    },
    {
      fieldname: "tax_template",
      label: __("Tax Template"),
      fieldtype: "Link",
      options: "Item Tax Template",
      reqd: 0,
      width: "100px",
    },
    {
      fieldname: "accounting_dimension",
      label: __("Accounting Dimension"),
      fieldtype: "Select",
      options: ["", "Cost Center", "Project"],
      default: "",
      reqd: 0,
      width: "120px",
    },
  ],

  formatter: function (value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);

    // Bold formatting for group header rows
    if (data && data.is_group_header) {
      if (
        [
          "taxable_value",
          "amount_of_vat",
          "name_of_purchaser",
          "accounting_dimension_value",
        ].includes(column.fieldname)
      ) {
        value = `<span style="font-weight: bold;">${value}</span>`;
      }
    }

    return value;
  },

  onload: function (report) {
    frappe.call({
      method: "frappe.client.get_list",
      args: {
        doctype: "Accounting Dimension",
        fields: ["document_type"],
        filters: {
          disabled: 0,
        },
      },
      callback: function (r) {
        let options = ["", "Cost Center", "Project"];
        if (r.message) {
          r.message.forEach(function (d) {
            if (!options.includes(d.document_type)) {
              options.push(d.document_type);
            }
          });
        }
        let dimension_filter = report.get_filter("accounting_dimension");
        if (dimension_filter) {
          dimension_filter.df.options = options;
          dimension_filter.refresh();
        }
      },
    });

    // All query reports share one page menu and Frappe never clears items added in onload, so remove
    // an "Export CSVs" left behind by another report (e.g. Kenya Purchase Tax Report) before adding ours.
    report.page.menu
      .find(".menu-item-label")
      .filter((_, label) => $(label).text().trim() === __("Export CSVs"))
      .closest("li")
      .remove();

    report.page.add_menu_item(__("Export CSVs"), function () {
      frappe.call({
        method:
          "csf_ke.csf_ke.report.kenya_sales_tax_report.kenya_sales_tax_report.download_custom_csv_format",
        args: {
          company: report.get_filter_value("company"),
          from_date: report.get_filter_value("from_date"),
          to_date: report.get_filter_value("to_date"),
        },
        freeze: true,
        freeze_message: __("Generating CSV files..."),
        callback: function (response) {
          if (response.message) {
            show_sales_csv_export_dialog(response.message);
          }
        },
      });
    });
  },
};

function show_sales_csv_export_dialog(result) {
  const templates = result.templates || [];
  const files = templates.filter((row) => row.file);

  if (!templates.length) {
    frappe.msgprint(
      __(
        "No submitted sales invoices with an Item Tax Template were found for this period.",
      ),
    );
    return;
  }

  const dialog = new frappe.ui.Dialog({
    title: __("Sales VAT CSVs"),
    size: "large",
    fields: [{ fieldtype: "HTML", fieldname: "summary" }],
    primary_action_label: __("Download All (.zip)"),
    primary_action() {
      open_url_post("/api/method/frappe.core.api.file.zip_files", {
        files: JSON.stringify(files.map((row) => row.file)),
      });
    },
    secondary_action_label: __("Go to Files"),
    secondary_action() {
      dialog.hide();
      // Plain List/File opens the folder view, which ignores these filters
      frappe.set_route("List", "File", "Report", {
        file_name: ["like", `%${result.timestamp}%`],
      });
    },
  });

  dialog.fields_dict.summary.$wrapper.html(
    get_sales_csv_export_summary_html(result, files.length),
  );
  dialog.get_primary_btn().prop("disabled", !files.length);
  dialog.show();
}

function get_sales_csv_export_summary_html(result, file_count) {
  const templates = result.templates;
  const escape = frappe.utils.escape_html;
  const currency = templates[0].currency;
  const money = (value) => format_currency(value, currency);
  const companies = [...new Set(templates.map((row) => row.company))];
  const show_company = companies.length > 1;
  const cell_style = "vertical-align: middle;";

  const rows = templates
    .map((row) => {
      const file_cell = row.file_url
        ? `<a href="${encodeURI(row.file_url)}" target="_blank">${__("Download")}</a>`
        : `<span class="text-muted">${__("No customers with PIN")}</span>`;

      return `<tr>
        ${show_company ? `<td style="${cell_style}">${escape(row.company)}</td>` : ""}
        <td style="${cell_style}">${escape(row.item_tax_template)}</td>
        <td class="text-right" style="${cell_style}">${row.invoice_count}</td>
        <td class="text-right" style="${cell_style}">${money(row.taxable_amount)}</td>
        <td class="text-right" style="${cell_style}">${money(row.vat_amount)}</td>
        <td class="text-center" style="${cell_style}">${file_cell}</td>
      </tr>`;
    })
    .join("");

  const notes = [];
  if (!file_count) {
    notes.push(
      __(
        "No CSV files were created: none of these invoices are for customers with a PIN.",
      ),
    );
  }
  if (result.skipped_no_pin.invoice_count) {
    notes.push(
      __(
        "{0} invoice(s) left out because the customer has no PIN (Taxable {1}, VAT {2}).",
        [
          result.skipped_no_pin.invoice_count,
          money(result.skipped_no_pin.taxable_amount),
          money(result.skipped_no_pin.vat_amount),
        ],
      ),
    );
  }
  if (result.invoices_without_template) {
    notes.push(
      __(
        "{0} invoice(s) have items without an Item Tax Template; those items are not in any CSV.",
        [result.invoices_without_template],
      ),
    );
  }

  return `
    <div class="mb-3">
      <div><span class="text-muted">${__("Company")}:</span> <b>${escape(companies.join(", "))}</b></div>
      <div><span class="text-muted">${__("Invoice Date")}:</span>
        <b>${frappe.datetime.str_to_user(result.from_date)}</b> ${__("to")}
        <b>${frappe.datetime.str_to_user(result.to_date)}</b>
      </div>
    </div>
    <div class="table-responsive">
      <table class="table table-bordered table-sm">
        <thead>
          <tr>
            ${show_company ? `<th>${__("Company")}</th>` : ""}
            <th>${__("Item Tax Template")}</th>
            <th class="text-right">${__("Invoices")}</th>
            <th class="text-right">${__("Taxable Amount")}</th>
            <th class="text-right">${__("VAT")}</th>
            <th class="text-center">${__("CSV")}</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
        <tfoot>
          <tr class="font-weight-bold">
            <td${show_company ? ' colspan="2"' : ""}>${__("Total")}</td>
            <td class="text-right">${result.totals.invoice_count}</td>
            <td class="text-right">${money(result.totals.taxable_amount)}</td>
            <td class="text-right">${money(result.totals.vat_amount)}</td>
            <td class="text-center">${__("{0} file(s)", [file_count])}</td>
          </tr>
        </tfoot>
      </table>
    </div>
    ${notes.map((note) => `<div class="alert alert-warning mb-2">${note}</div>`).join("")}
  `;
}

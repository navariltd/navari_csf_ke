// Copyright (c) 2022, Navari Limited and contributors
// For license information, please see license.txt

frappe.query_reports["Kenya Purchase Tax Report"] = {
  filters: [
    {
      fieldname: "company",
      label: __("Company"),
      fieldtype: "Link",
      options: "Company",
      default: frappe.defaults.get_default("company"),
      reqd: 1,
    },
    {
      fieldname: "from_date",
      label: __("From Date"),
      fieldtype: "Date",
      default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
      reqd: 1,
    },
    {
      fieldname: "to_date",
      label: __("To Date"),
      fieldtype: "Date",
      default: frappe.datetime.get_today(),
      reqd: 1,
    },
    {
      fieldname: "item_tax_template",
      label: __("Item Tax Template"),
      fieldtype: "Link",
      options: "Item Tax Template",
      reqd: 0,
      hidden: 1,
    },
    {
      fieldname: "taxes_and_charges_template",
      label: __("Purchase Taxes and Charges Template"),
      fieldtype: "Link",
      options: "Purchase Taxes and Charges Template",
      reqd: 0,
      hidden: 1,
    },
    {
      fieldname: "accounting_dimension",
      label: __("Accounting Dimension"),
      fieldtype: "Select",
      options: ["", "Cost Center", "Project"],
      default: "",
      reqd: 0,
    },
    {
      fieldname: "is_return",
      label: __("Is Return"),
      fieldtype: "Check",
      default: 0,
      reqd: 0,
    },
  ],

  formatter: function (value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);

    if (data && data.is_group_header) {
      if (
        [
          "accounting_dimension_value",
          "party_name",
          "taxable_amount",
          "vat_amount",
        ].includes(column.fieldname)
      ) {
        value = `<span style="font-weight: bold;">${value}</span>`;
      }
    }

    return value;
  },

  onload: function (report) {
    frappe.call({
      method: "frappe.client.get_value",
      args: {
        doctype: "Accounts Settings",
        fieldname: [
          "add_taxes_from_item_tax_template",
          "add_taxes_from_taxes_and_charges_template",
        ],
      },
      callback: function (r) {
        if (r.message) {
          const item_tax_template_filter =
            report.get_filter("item_tax_template");
          const taxes_and_charges_filter = report.get_filter(
            "taxes_and_charges_template",
          );
          if (item_tax_template_filter) {
            item_tax_template_filter.df.hidden =
              !r.message.add_taxes_from_item_tax_template;
            taxes_and_charges_filter.set_value("");
            item_tax_template_filter.refresh();
          }

          if (taxes_and_charges_filter) {
            taxes_and_charges_filter.df.hidden =
              !r.message.add_taxes_from_taxes_and_charges_template;
            item_tax_template_filter.set_value("");
            taxes_and_charges_filter.refresh();
          }
        }
      },
    });

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

    // Report filters only show their label on hover, so spell out the date field being filtered
    [
      ["from_date", __("From Supplier Invoice Date (bill_date)")],
      ["to_date", __("To Supplier Invoice Date (bill_date)")],
    ].forEach(([fieldname, title]) => {
      const filter = report.get_filter(fieldname);
      if (filter) {
        $(filter.wrapper)
          .attr("title", title)
          .attr("data-original-title", title);
      }
    });

    report.page.add_menu_item(__("Export CSVs"), function () {
      frappe.call({
        method:
          "csf_ke.csf_ke.report.kenya_purchase_tax_report.kenya_purchase_tax_report.download_custom_csv_format",
        args: {
          company: report.get_filter_value("company"),
          from_date: report.get_filter_value("from_date"),
          to_date: report.get_filter_value("to_date"),
        },
        freeze: true,
        freeze_message: __("Generating CSV files..."),
        callback: function (response) {
          if (response.message) {
            show_purchase_csv_export_dialog(response.message);
          }
        },
      });
    });
  },
};

function show_purchase_csv_export_dialog(result) {
  const templates = result.templates || [];
  const files = templates.filter((row) => row.file);

  if (!templates.length) {
    frappe.msgprint(
      __(
        "No submitted purchase invoices with an Item Tax Template were found for this period.",
      ),
    );
    return;
  }

  const dialog = new frappe.ui.Dialog({
    title: __("Purchase VAT CSVs"),
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
      frappe.set_route("List", "File", "Report", {
        file_name: ["like", `%${result.timestamp}%`],
      });
    },
  });

  dialog.fields_dict.summary.$wrapper.html(
    get_purchase_csv_export_summary_html(result, files.length),
  );
  dialog.get_primary_btn().prop("disabled", !files.length);
  dialog.show();
}

function get_purchase_csv_export_summary_html(result, file_count) {
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
        : `<span class="text-muted">${__("No suppliers with PIN")}</span>`;

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
        "No CSV files were created: none of these invoices are from suppliers with a PIN.",
      ),
    );
  }
  if (result.skipped_no_pin.invoice_count) {
    notes.push(
      __(
        "{0} invoice(s) left out because the supplier has no PIN (Taxable {1}, VAT {2}).",
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
      <div><span class="text-muted">${__("Supplier Invoice Date")}:</span>
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

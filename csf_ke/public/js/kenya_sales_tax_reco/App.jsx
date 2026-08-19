import * as React from "react";

const STATUS_META = {
  matched: {
    label: "Matched",
    badgeClass: "kstr-status-matched",
    rowClass: "",
  },
  only_in_system: {
    label: "Local Only",
    badgeClass: "kstr-status-system",
    rowClass: "kstr-row-system-only",
  },
  only_in_upload: {
    label: "In Upload Only",
    badgeClass: "kstr-status-upload",
    rowClass: "kstr-row-upload-only",
  },
};

const RECONCILIATION_METHOD =
  "csf_ke.csf_ke.doctype.kenya_sales_reconciliation.kenya_sales_reconciliation.reconcile";
const GET_DOC_METHOD =
  "csf_ke.csf_ke.doctype.kenya_sales_reconciliation.kenya_sales_reconciliation.get_reconciliation_doc";
const LIST_DOCS_METHOD =
  "csf_ke.csf_ke.doctype.kenya_sales_reconciliation.kenya_sales_reconciliation.list_reconciliation_docs";

const COLUMNS = [
  { key: "etr_invoice_number", label: "SCU Invoice No" },
  { key: "name_of_purchaser", label: "Name" },
  { key: "pin_of_purchaser", label: "PIN" },
  { key: "cu_invoice_date", label: "Date" },
  { key: "taxable_value", label: "Amount", numeric: true },
  { key: "invoice_name", label: "Sales Invoice" },
];

/** Format a Date as ISO string (YYYY-MM-DD) using local time. */
function formatDate(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

/** Return today's date as ISO string (YYYY-MM-DD). */
function todayStr() {
  return formatDate(new Date());
}

/**
 * Compute the default reconciliation date range.
 *
 * Uses a full calendar month:
 *   - If today is the last day of the month → current month (1st → today)
 *   - Otherwise → the previous full calendar month (1st → last day)
 */
function getDefaultDateRange() {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const lastDayOfMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0);

  if (today.getTime() === lastDayOfMonth.getTime()) {
    return {
      from_date: formatDate(new Date(now.getFullYear(), now.getMonth(), 1)),
      to_date: formatDate(lastDayOfMonth),
    };
  }

  return {
    from_date: formatDate(new Date(now.getFullYear(), now.getMonth() - 1, 1)),
    to_date: formatDate(new Date(now.getFullYear(), now.getMonth(), 0)),
  };
}

/** Pick the user's default company, falling back to the first available. */
function getDefaultCompany(companies) {
  const bootDefault = frappe.boot?.user_companies?.default_company;
  if (bootDefault && companies.includes(bootDefault)) return bootDefault;
  return companies[0] || "";
}

export function App() {
  // Filters
  const [company, setCompany] = React.useState("");
  const [companies, setCompanies] = React.useState([]);
  const [taxTemplates, setTaxTemplates] = React.useState([]);
  const [fromDate, setFromDate] = React.useState("");
  const [toDate, setToDate] = React.useState("");
  const [isReturn, setIsReturn] = React.useState("");
  const [taxTemplate, setTaxTemplate] = React.useState("");

  // File / Save state
  const [fileUrls, setFileUrls] = React.useState([]);
  const [fileNames, setFileNames] = React.useState({}); // url -> name
  const [docName, setDocName] = React.useState("");
  const [loadingDocName, setLoadingDocName] = React.useState("");

  // Results
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState("");
  const [result, setResult] = React.useState(null);
  const [activeTab, setActiveTab] = React.useState("all");
  const [uploadErrors, setUploadErrors] = React.useState([]);
  const [dragOver, setDragOver] = React.useState(false);
  const [expandedSummaryCards, setExpandedSummaryCards] = React.useState({});

  // Recent docs
  const [recentDocs, setRecentDocs] = React.useState([]);
  const [showRecent, setShowRecent] = React.useState(false);

  // Collapsible sections — default expanded
  const [collapsedSections, setCollapsedSections] = React.useState({
    filters: false,
    upload: false,
    results: false,
  });

  const today = todayStr();

  // Init: load companies, tax templates, load doc from URL params
  React.useEffect(() => {
    loadCompanies();
    loadTaxTemplates();

    const params = getRouteParams();
    const docNameParam = params.id || params.doc_name || params.docname || "";

    if (docNameParam) {
      loadReconciliationDoc(docNameParam);
    } else {
      if (params.company) setCompany(params.company);
      if (params.is_return) setIsReturn(params.is_return);
      if (params.tax_template) setTaxTemplate(params.tax_template);
      if (params.file_urls) {
        const urls =
          typeof params.file_urls === "string"
            ? JSON.parse(params.file_urls)
            : params.file_urls;
        if (Array.isArray(urls)) setFileUrls(urls);
      }
      // Auto-set dates — use route params if provided, otherwise default to full month range
      const { from_date: defaultFrom, to_date: defaultTo } =
        getDefaultDateRange();
      setFromDate(params.from_date || defaultFrom);
      setToDate(params.to_date || defaultTo);
    }
  }, []);

  // Derived flag: run button only shows when all prerequisites are met
  const canRun = Boolean(
    company &&
    fromDate &&
    toDate &&
    fileUrls.length > 0 &&
    fromDate <= today &&
    toDate <= today &&
    fromDate <= toDate,
  );

  function getRouteParams() {
    return frappe.route_options || {};
  }

  function setRouteParams(params) {
    // Store on frappe.route_options so back button / reload works
    frappe.route_options = { ...(frappe.route_options || {}), ...params };
    updateUrlParams(params);
  }

  function updateUrlParams(params) {
    // Update the actual URL query string so it can be shared/bookmarked
    try {
      const url = new URL(window.location.href);
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== "") {
          url.searchParams.set(key, String(value));
        } else {
          url.searchParams.delete(key);
        }
      });
      // Update without full reload
      history.replaceState(null, "", url.pathname + url.search + url.hash);
    } catch {
      // ignore URL update errors in non-browser/test contexts
    }
  }

  async function loadReconciliationDoc(docNameParam) {
    if (!docNameParam) return;
    setLoadingDocName(docNameParam);
    try {
      const resp = await frappe.call({
        method: GET_DOC_METHOD,
        args: { doc_name: docNameParam },
      });
      const data = resp.message;
      if (!data) {
        setError(`Reconciliation document "${docNameParam}" not found`);
        return;
      }
      setDocName(data.doc_name);
      setCompany(data.company || "");
      setFromDate(data.from_date || "");
      setToDate(data.to_date || "");
      setIsReturn(data.is_return || "");
      setTaxTemplate(data.tax_template || "");
      if (data.file_urls) setFileUrls(data.file_urls);
      const results = data.results || {};
      setResult(results);
      setActiveTab("summary");

      // set URL params
      setRouteParams({ doc_name: data.doc_name });
    } catch (e) {
      setError(e.message || `Failed to load document "${docNameParam}"`);
    } finally {
      setLoadingDocName("");
    }
  }

  async function loadTaxTemplates() {
    try {
      const resp = await frappe.call({
        method: "frappe.client.get_list",
        args: {
          doctype: "Item Tax Template",
          fields: ["name"],
          limit_page_length: 0,
          order_by: "name asc",
        },
      });
      if (resp.message && resp.message.length) {
        setTaxTemplates(resp.message.map((t) => t.name));
      }
    } catch {
      // silently ignore if no tax templates exist
    }
  }

  async function loadCompanies() {
    try {
      const resp = await frappe.call({
        method: "frappe.client.get_list",
        args: {
          doctype: "Company",
          fields: ["name"],
          limit_page_length: 0,
          order_by: "name asc",
        },
      });
      if (resp.message && resp.message.length) {
        const names = resp.message.map((c) => c.name);
        setCompanies(names);
        // Auto-pick the default company if company not already set
        setCompany((current) => current || getDefaultCompany(names));
      }
    } catch (e) {
      setError(e.message || "Failed to load companies");
    }
  }

  async function handleReconcile() {
    // Validate again before actually running (defensive)
    if (!company) {
      setError("Company is required");
      return;
    }
    if (!fromDate || !toDate) {
      setError("From and To dates are required");
      return;
    }
    if (fromDate > toDate) {
      setError("To date must be on or after the From date");
      return;
    }
    if (toDate > today) {
      setError(`To date cannot be in the future (max: ${today})`);
      return;
    }
    if (fromDate > today) {
      setError(`From date cannot be in the future (max: ${today})`);
      return;
    }
    if (!fileUrls.length) {
      setError("Please upload at least one CSV file");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const resp = await frappe.call({
        method: RECONCILIATION_METHOD,
        args: {
          company,
          from_date: fromDate,
          to_date: toDate,
          file_urls: fileUrls,
          is_return: isReturn,
          tax_template: taxTemplate,
          save_doc: true,
          doc_name: docName || undefined,
        },
      });
      const msg = resp.message;
      setResult(msg);
      setActiveTab("summary");

      if (msg.doc_name) {
        setDocName(msg.doc_name);
        setRouteParams({ doc_name: msg.doc_name });
        frappe.show_alert({
          message: __(`Saved as ${msg.doc_name}`),
          indicator: "green",
        });
      } else {
        frappe.show_alert({
          message: __("Reconciliation completed"),
          indicator: "blue",
        });
      }
    } catch (e) {
      setError(e.message || "Reconciliation failed");
    } finally {
      setLoading(false);
    }
  }

  function openFileDialog() {
    new frappe.ui.FileUploader({
      folder: "Home",
      restrictions: { allowed_file_types: [".csv"] },
      multiple: true,
      on_success: (file_doc) => {
        setFileUrls((prev) => [...prev, file_doc.file_url]);
        setFileNames((prev) => ({
          ...prev,
          [file_doc.file_url]:
            file_doc.file_name || file_doc.file_url.split("/").pop(),
        }));
        frappe.show_alert({
          message: __(`Uploaded ${file_doc.file_name}`),
          indicator: "green",
        });
      },
      onerror: (message) => {
        setUploadErrors((prev) => [...prev, message]);
      },
    });
  }

  function handleDragOver(e) {
    e.preventDefault();
    setDragOver(true);
  }

  function handleDragLeave() {
    setDragOver(false);
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    const files = Array.from(e.dataTransfer.files || []);
    if (!files.length) return;
    new frappe.ui.FileUploader({
      folder: "Home",
      restrictions: { allowed_file_types: [".csv"] },
      multiple: true,
      on_success: (file_doc) => {
        setFileUrls((prev) => [...prev, file_doc.file_url]);
        setFileNames((prev) => ({
          ...prev,
          [file_doc.file_url]: file_doc.file_name || "",
        }));
        frappe.show_alert({
          message: __(`Uploaded ${file_doc.file_name}`),
          indicator: "green",
        });
      },
      onerror: (message) => {
        setUploadErrors((prev) => [...prev, message]);
      },
    }).upload_files(files);
  }

  function removeFileUrl(fileUrl) {
    setFileUrls((prev) => prev.filter((u) => u !== fileUrl));
    setFileNames((prev) => {
      const next = { ...prev };
      delete next[fileUrl];
      return next;
    });
  }

  function resetFiles() {
    setFileUrls([]);
    setFileNames({});
    setUploadErrors([]);
  }

  async function downloadReport() {
    if (!company || !fromDate || !toDate) {
      setError("Company, From date and To date are required for export");
      return;
    }
    try {
      const resp = await frappe.call({
        method:
          "csf_ke.csf_ke.report.kenya_sales_tax_report.kenya_sales_tax_report.download_custom_csv_format",
        args: { company, from_date: fromDate, to_date: toDate },
      });
      if (resp.message) {
        Object.entries(resp.message).forEach(([, url]) => {
          window.open(url, "_blank");
        });
      } else {
        frappe.msgprint(
          __("No CSV files generated for the selected date range."),
        );
      }
    } catch (e) {
      setError(e.message || "Export failed");
    }
  }

  async function loadRecentDocs() {
    try {
      const resp = await frappe.call({
        method: LIST_DOCS_METHOD,
        args: { limit: 10 },
      });
      setRecentDocs(resp.message || []);
      setShowRecent(true);
    } catch (e) {
      setError(e.message || "Failed to list saved reconciliations");
    }
  }

  function exportResults() {
    if (!result) return;
    const rows = combinedResults();
    if (!rows.length) {
      frappe.msgprint(__("No rows to export"));
      return;
    }
    const headers = [
      "Status",
      "SCU Invoice No",
      "Name",
      "PIN",
      "Date",
      "Amount",
      "Sales Invoice",
    ];
    const csv = rows
      .map((r) =>
        [
          STATUS_META[r.status]?.label || r.status,
          r.etr_invoice_number,
          r.name_of_purchaser,
          r.pin_of_purchaser,
          r.cu_invoice_date,
          r.taxable_value,
          r.invoice_name,
        ]
          .map((cell) => `"${String(cell ?? "").replace(/"/g, '""')}"`)
          .join(","),
      )
      .join("\n");
    const blob = new Blob([`${headers.join(",")}\n${csv}`], {
      type: "text/csv;charset=utf-8;",
    });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `kenya_sales_tax_reco_${fromDate}_to_${toDate}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function combinedResults() {
    if (!result) return [];
    return [
      ...(result.only_in_system || []).map((r) => ({
        ...r,
        status: "only_in_system",
      })),
      ...(result.only_in_upload || []).map((r) => ({
        ...r,
        status: "only_in_upload",
      })),
      ...(result.matched || []).map((r) => ({ ...r, status: "matched" })),
    ];
  }

  // Toggle collapsible card sections — single click
  function toggleSection(key) {
    setCollapsedSections((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  // Toggle a summary card's rows (Local or individual file card)
  // Treat undefined (default) as expanded — first click must collapse
  function toggleSummaryCard(key) {
    setExpandedSummaryCards((prev) => {
      const isCurrentlyExpanded = prev[key] !== false;
      return { ...prev, [key]: !isCurrentlyExpanded };
    });
  }

  // Start a brand-new reconciliation (clear all filters, results, and files)
  function handleNewRecon() {
    setCompany(getDefaultCompany(companies));
    const { from_date: defaultFrom, to_date: defaultTo } =
      getDefaultDateRange();
    setFromDate(defaultFrom);
    setToDate(defaultTo);
    setIsReturn("");
    setTaxTemplate("");
    setFileUrls([]);
    setFileNames({});
    setUploadErrors([]);
    setDocName("");
    setResult(null);
    setError("");
    setActiveTab("summary");
    setShowRecent(false);
    // Clear route params / URL query so reload gives a fresh page
    setRouteParams({});
    frappe.route_options = {};
    try {
      const url = new URL(window.location.href);
      url.search = "";
      history.replaceState(null, "", url.pathname + url.search + url.hash);
    } catch {
      // ignore
    }
  }

  const counts = {
    system: result ? (result.system_rows || []).length : 0,
    upload: result ? (result.upload_rows || []).length : 0,
    matched: result ? (result.matched || []).length : 0,
    onlySystem: result ? (result.only_in_system || []).length : 0,
    onlyUpload: result ? (result.only_in_upload || []).length : 0,
  };

  function getActiveRows() {
    if (!result) return [];
    return combinedResults();
  }

  function getFileName(url) {
    if (fileNames[url]) return fileNames[url];
    return url.split("/").pop();
  }

  // Mandatory-field error flags (red border when missing)
  const missingCompany = !company;
  const missingFromDate = !fromDate;
  const missingToDate = !toDate;
  const missingFiles = fileUrls.length === 0;
  const invalidDateRange = Boolean(fromDate && toDate && fromDate > toDate);
  const futureDates = Boolean(fromDate && (fromDate > today || toDate > today));

  return (
    <div className="kstr-page">
      <div className="kstr-header">
        <div className="kstr-header-left">
          <h3>Kenya Sales Tax Reconciliation</h3>
          <p>
            {docName
              ? `Editing: ${docName}`
              : "Compare the system Sales Tax Report against uploaded eTIMS CSV files"}
          </p>
        </div>
        <div className="kstr-header-actions">
          <button
            className="kstr-btn kstr-btn-cream"
            onClick={handleNewRecon}
            title="Start a brand-new reconciliation"
          >
            <span className="kstr-btn-icon">＋</span> New Recon
          </button>
          <button className="kstr-btn kstr-btn-cream" onClick={loadRecentDocs}>
            <span className="kstr-btn-icon">📋</span> Recent
          </button>
          <button className="kstr-btn kstr-btn-cream" onClick={downloadReport}>
            <span className="kstr-btn-icon">⤓</span> Export System CSVs
          </button>
          {result && (
            <button className="kstr-btn kstr-btn-cream" onClick={exportResults}>
              <span className="kstr-btn-icon">⤓</span> Export Results
            </button>
          )}
        </div>
      </div>

      {showRecent && (
        <div className="kstr-card">
          <div className="kstr-card-header">
            <h4>Saved Reconciliations</h4>
            <p>Click a record to load its saved state</p>
          </div>
          <div className="kstr-card-body">
            {recentDocs.length ? (
              <div className="kstr-table-wrap">
                <table className="kstr-table">
                  <thead>
                    <tr>
                      <th>Document</th>
                      <th>Company</th>
                      <th>From</th>
                      <th>To</th>
                      <th>Last Run</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentDocs.map((doc) => (
                      <tr key={doc.name}>
                        <td>{doc.name}</td>
                        <td>{doc.company}</td>
                        <td>{doc.from_date}</td>
                        <td>{doc.to_date}</td>
                        <td>{doc.last_run || "-"}</td>
                        <td>
                          <a
                            className="kstr-btn kstr-btn-outline-light kstr-btn-sm"
                            style={{ textDecoration: "none" }}
                            href={`#/kenya-sales-tax-reco?doc_name=${doc.name}`}
                            onClick={(e) => {
                              e.preventDefault();
                              frappe.set_route("kenya-sales-tax-reco", {
                                doc_name: doc.name,
                              });
                            }}
                          >
                            Load
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="kstr-empty-state">
                No saved reconciliations found
              </div>
            )}
            <button
              className="kstr-btn kstr-btn-outline-light"
              style={{ marginTop: "12px" }}
              onClick={() => setShowRecent(false)}
            >
              Close
            </button>
          </div>
        </div>
      )}

      {loadingDocName && (
        <div className="kstr-info">
          Loading reconciliation {loadingDocName}…
        </div>
      )}

      {/* Filters Card — collapsible */}
      <div className="kstr-card">
        <div
          className={`kstr-accordion-header ${!collapsedSections.filters ? "kstr-expanded" : ""}`}
          onClick={() => toggleSection("filters")}
          role="button"
          tabIndex={0}
          aria-expanded={!collapsedSections.filters}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              toggleSection("filters");
            }
          }}
        >
          <span className="kstr-accordion-icon">⚙</span>
          <div className="kstr-accordion-text">
            <h4>Filters</h4>
            <p>Select company, date range and reconciliation parameters</p>
          </div>
          <span className="kstr-accordion-chevron">▾</span>
        </div>
        <div
          className={`kstr-accordion-body ${collapsedSections.filters ? "kstr-collapsed" : ""}`}
        >
          <div className="kstr-card-body">
            <div className="kstr-toolbar">
              <div
                className={`kstr-field ${missingCompany ? "kstr-field-error" : ""}`}
              >
                <label>
                  Company <span className="kstr-required">*</span>
                </label>
                <select
                  className={missingCompany ? "kstr-input-error" : ""}
                  value={company}
                  onChange={(e) => {
                    setCompany(e.target.value);
                    setRouteParams({ company: e.target.value });
                  }}
                >
                  <option value="">Select Company</option>
                  {companies.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>

              <div
                className={`kstr-field ${missingFromDate || invalidDateRange || futureDates ? "kstr-field-error" : ""}`}
              >
                <label>
                  From Date <span className="kstr-required">*</span>
                </label>
                <input
                  className={
                    missingFromDate || invalidDateRange || futureDates
                      ? "kstr-input-error"
                      : ""
                  }
                  type="date"
                  value={fromDate}
                  max={today}
                  onChange={(e) => {
                    const nextFrom = e.target.value;
                    setFromDate(nextFrom);
                    // Auto-adjust To date so it never precedes the new From date
                    if (toDate && nextFrom && nextFrom > toDate) {
                      setToDate(nextFrom);
                    }
                    setRouteParams({ from_date: nextFrom });
                  }}
                />
              </div>

              <div
                className={`kstr-field ${missingToDate || invalidDateRange || futureDates ? "kstr-field-error" : ""}`}
              >
                <label>
                  To Date <span className="kstr-required">*</span>
                </label>
                <input
                  className={
                    missingToDate || invalidDateRange || futureDates
                      ? "kstr-input-error"
                      : ""
                  }
                  type="date"
                  value={toDate}
                  min={fromDate || undefined}
                  max={today}
                  onChange={(e) => {
                    setToDate(e.target.value);
                    setRouteParams({ to_date: e.target.value });
                  }}
                />
              </div>

              <div className="kstr-field">
                <label>Is Return</label>
                <select
                  value={isReturn}
                  onChange={(e) => {
                    setIsReturn(e.target.value);
                    setRouteParams({ is_return: e.target.value });
                  }}
                >
                  <option value="">All</option>
                  <option value="Is Return">Is Return</option>
                  <option value="Normal Sales Invoice">
                    Normal Sales Invoice
                  </option>
                </select>
              </div>

              <div className="kstr-field">
                <label>Tax Template</label>
                <select
                  value={taxTemplate}
                  onChange={(e) => {
                    setTaxTemplate(e.target.value);
                    setRouteParams({ tax_template: e.target.value });
                  }}
                >
                  <option value="">All Templates</option>
                  {taxTemplates.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>

              <div className="kstr-field">
                <label>Run</label>
                {canRun ? (
                  <button
                    className="kstr-btn kstr-btn-primary"
                    onClick={handleReconcile}
                    disabled={loading}
                  >
                    {loading ? (
                      <>
                        <span className="kstr-spinner" /> Reconciling…
                      </>
                    ) : docName ? (
                      "Save & Re-run"
                    ) : (
                      "Run Reconciliation"
                    )}
                  </button>
                ) : (
                  <div className="kstr-readiness">
                    <span className="kstr-readiness-icon">🔒</span>
                    Complete required fields to run
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Upload Card — collapsible */}
      <div className="kstr-card">
        <div
          className={`kstr-accordion-header ${!collapsedSections.upload ? "kstr-expanded" : ""}`}
          onClick={() => toggleSection("upload")}
          role="button"
          tabIndex={0}
          aria-expanded={!collapsedSections.upload}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              toggleSection("upload");
            }
          }}
        >
          <span className="kstr-accordion-icon">📁</span>
          <div className="kstr-accordion-text">
            <h4>
              CSV Uploads{" "}
              {fileUrls.length > 0 && (
                <span className="kstr-badge-count">{fileUrls.length}</span>
              )}
            </h4>
            <p>
              {docName
                ? "Drop additional files to add them, then Save & Re-run"
                : "Upload one or more eTIMS CSV files — column layout is auto-detected"}
            </p>
          </div>
          <span className="kstr-accordion-chevron">▾</span>
        </div>
        <div
          className={`kstr-accordion-body ${collapsedSections.upload ? "kstr-collapsed" : ""}`}
        >
          <div className="kstr-card-body">
            <div
              className={`kstr-upload-zone ${dragOver ? "kstr-dragover" : ""} ${
                missingFiles ? "kstr-upload-zone-error" : ""
              }`}
              onClick={openFileDialog}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <span className="kstr-required-req">* Required</span>
              <span className="kstr-upload-icon">📁</span>
              <p className="kstr-upload-title">
                {fileUrls.length
                  ? "Upload Additional CSV Files"
                  : "Click to upload CSV files"}
              </p>
              <p className="kstr-upload-subtitle">
                or drag & drop files here (SEC B, SEC D1, SEC E formats
                supported)
              </p>
            </div>

            {fileUrls.length > 0 && (
              <div className="kstr-uploaded-files">
                <span className="kstr-uploaded-label">
                  <strong>{fileUrls.length}</strong> file(s) uploaded
                </span>
                <div className="kstr-file-list">
                  {fileUrls.map((url) => (
                    <span key={url} className="kstr-file-chip">
                      {getFileName(url)}
                      <button
                        onClick={() => removeFileUrl(url)}
                        aria-label="Remove file"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
                <div className="kstr-btn-group" style={{ marginTop: "12px" }}>
                  <button
                    className="kstr-btn kstr-btn-success"
                    onClick={openFileDialog}
                  >
                    + Add More
                  </button>
                  <button
                    className="kstr-btn kstr-btn-outline-danger"
                    onClick={resetFiles}
                  >
                    Clear All
                  </button>
                </div>
              </div>
            )}

            {uploadErrors.length > 0 && (
              <div className="kstr-errors">
                {uploadErrors.map((err, i) => (
                  <div key={i}>{err}</div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {error && <div className="kstr-error">{error}</div>}

      {/* Results Card — collapsible */}
      {result && (
        <div className="kstr-card">
          <div
            className={`kstr-accordion-header ${!collapsedSections.results ? "kstr-expanded" : ""}`}
            onClick={() => toggleSection("results")}
            role="button"
            tabIndex={0}
            aria-expanded={!collapsedSections.results}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                toggleSection("results");
              }
            }}
          >
            <span className="kstr-accordion-icon">📊</span>
            <div className="kstr-accordion-text">
              <h4>
                Reconciliation Results{" "}
                {docName && (
                  <span style={{ fontWeight: 400, color: "#64748b" }}>
                    — {docName}
                  </span>
                )}
              </h4>
              <p>
                {counts.matched} matched · {counts.onlySystem} Local only ·{" "}
                {counts.onlyUpload} in upload only
              </p>
            </div>
            <span className="kstr-accordion-chevron">▾</span>
          </div>
          <div
            className={`kstr-accordion-body ${collapsedSections.results ? "kstr-collapsed" : ""}`}
          >
            <div className="kstr-card-body">
              <div className="kstr-stats">
                <div className="kstr-stat kstr-stat-blue">
                  <span className="kstr-stat-label">System Rows</span>
                  <span className="kstr-stat-value">{counts.system}</span>
                </div>
                <div className="kstr-stat kstr-stat-green">
                  <span className="kstr-stat-label">Upload Rows</span>
                  <span className="kstr-stat-value">{counts.upload}</span>
                </div>
                <div className="kstr-stat kstr-stat-emerald">
                  <span className="kstr-stat-label">Matched</span>
                  <span className="kstr-stat-value">{counts.matched}</span>
                </div>
                <div className="kstr-stat kstr-stat-red">
                  <span className="kstr-stat-label">Local Only</span>
                  <span className="kstr-stat-value">{counts.onlySystem}</span>
                </div>
                <div className="kstr-stat kstr-stat-amber">
                  <span className="kstr-stat-label">In Upload Only</span>
                  <span className="kstr-stat-value">{counts.onlyUpload}</span>
                </div>
              </div>

              <div className="kstr-tabs">
                {[
                  {
                    id: "summary",
                    label: `Summary (Errors: ${counts.onlySystem + counts.onlyUpload})`,
                  },
                  {
                    id: "all",
                    label: `All (${counts.system + counts.upload})`,
                  },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    className={`kstr-tab ${activeTab === tab.id ? "kstr-active" : ""}`}
                    onClick={() => setActiveTab(tab.id)}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              <div>
                {activeTab === "summary" ? (
                  <div className="kstr-summary-grid">
                    {/* Local card — collapsible */}
                    {(() => {
                      const key = "system";
                      const isExpanded = expandedSummaryCards[key] !== false;
                      return (
                        <div className="kstr-summary-card kstr-summary-danger">
                          <button
                            className={`kstr-summary-header kstr-collapsible-summary ${isExpanded ? "kstr-expanded" : ""}`}
                            onClick={() => toggleSummaryCard(key)}
                            aria-expanded={isExpanded}
                          >
                            Local — Missing in Upload
                            <span className="kstr-summary-count">
                              {counts.onlySystem} row(s)
                            </span>
                            <span className="kstr-summary-chevron">▾</span>
                          </button>
                          <div
                            className={`kstr-summary-body ${isExpanded ? "kstr-open" : ""}`}
                          >
                            <ul className="kstr-summary-list">
                              {(result.only_in_system || []).map((r, idx) => (
                                <li key={idx}>
                                  <span className="kstr-scu-number">
                                    {r.etr_invoice_number}
                                  </span>
                                  <span className="kstr-customer-name">
                                    {r.name_of_purchaser}
                                  </span>
                                </li>
                              ))}
                              {counts.onlySystem === 0 && (
                                <li>
                                  <span className="kstr-empty">No records</span>
                                </li>
                              )}
                            </ul>
                          </div>
                        </div>
                      );
                    })()}

                    {/* One full card per uploaded file — collapsible */}
                    {fileUrls.map((url) => {
                      const fileRows = (result.only_in_upload || []).filter(
                        (r) => (r.file_url || "") === url,
                      );
                      const isExpanded = expandedSummaryCards[url] !== false;
                      return (
                        <div
                          key={url}
                          className="kstr-summary-card kstr-summary-warning"
                        >
                          <button
                            className={`kstr-summary-header kstr-collapsible-summary ${isExpanded ? "kstr-expanded" : ""}`}
                            onClick={() => toggleSummaryCard(url)}
                            aria-expanded={isExpanded}
                          >
                            {getFileName(url)} — Missing
                            <span className="kstr-summary-count">
                              {fileRows.length} row(s)
                            </span>
                            <span className="kstr-summary-chevron">▾</span>
                          </button>
                          <div
                            className={`kstr-summary-body ${isExpanded ? "kstr-open" : ""}`}
                          >
                            <ul className="kstr-summary-list">
                              {fileRows.map((r, idx) => (
                                <li key={idx}>
                                  <span className="kstr-scu-number">
                                    {r.etr_invoice_number}
                                  </span>
                                  <span className="kstr-customer-name">
                                    {r.name_of_purchaser}
                                  </span>
                                </li>
                              ))}
                              {fileRows.length === 0 && (
                                <li>
                                  <span className="kstr-empty">No records</span>
                                </li>
                              )}
                            </ul>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <GroupedTabResults
                    activeTab="all"
                    result={result}
                    fileUrls={fileUrls}
                    fileNames={fileNames}
                    getFileName={getFileName}
                    expandedSummaryCards={expandedSummaryCards}
                    toggleSummaryCard={toggleSummaryCard}
                  />
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function GroupedTabResults({
  activeTab,
  result,
  fileUrls,
  fileNames,
  getFileName,
  expandedSummaryCards,
  toggleSummaryCard,
}) {
  const isAll = activeTab === "all";

  // Local: ALL system rows (matched + only_in_system) with status
  const systemRows = (result?.system_rows || []).map((row) => ({
    ...row,
    status: (result?.matched || []).some(
      (m) => m.etr_invoice_number === row.etr_invoice_number,
    )
      ? "matched"
      : "only_in_system",
  }));

  // Group ALL upload rows by file (matched + only_in_upload) with status
  const uploadGroups = (fileUrls || []).map((url) => {
    const fileRows = (result?.upload_rows || []).filter(
      (r) => (r.file_url || "") === url,
    );
    return {
      url,
      rows: fileRows.map((row) => ({
        ...row,
        status: (result?.matched || []).some(
          (m) => m.etr_invoice_number === row.etr_invoice_number,
        )
          ? "matched"
          : "only_in_upload",
      })),
    };
  });

  // Build card list
  const cards = [];

  // Local card first — ALL system rows with status
  cards.push({
    key: "system",
    title: "Local",
    icon: "💻",
    type: "warning",
    rows: systemRows,
    count: systemRows.length,
  });

  // One card per file — ALL upload rows for that file with status
  uploadGroups.forEach((group) => {
    cards.push({
      key: group.url,
      title: `${getFileName(group.url)}`,
      icon: "📄",
      type: "warning",
      rows: group.rows,
      count: group.rows.length,
    });
  });

  // If no cards have content, show empty state
  if (!cards.length || cards.every((c) => c.count === 0)) {
    return <div className="kstr-empty-state">No records found.</div>;
  }

  return (
    <div className="kstr-summary-grid">
      {cards.map((card) => {
        const isExpanded = expandedSummaryCards[card.key] !== false;
        return (
          <div
            key={card.key}
            className={`kstr-summary-card kstr-summary-${card.type}`}
          >
            <button
              className={`kstr-summary-header kstr-collapsible-summary ${isExpanded ? "kstr-expanded" : ""}`}
              onClick={() => toggleSummaryCard(card.key)}
              aria-expanded={isExpanded}
            >
              <span className="kstr-group-icon">{card.icon}</span>
              {card.title}
              <span className="kstr-summary-count">{card.count} row(s)</span>
              <span className="kstr-summary-chevron">▾</span>
            </button>
            <div
              className={`kstr-summary-body ${isExpanded ? "kstr-open" : ""}`}
            >
              <div className="kstr-table-wrap kstr-grouped-table">
                <table className="kstr-table">
                  <thead>
                    <tr>
                      <th>Reconciled</th>
                      <th>SCU Invoice No</th>
                      <th>Name</th>
                      <th>PIN</th>
                      <th>Date</th>
                      <th className="kstr-text-right">Amount</th>
                      <th>Sales Invoice</th>
                    </tr>
                  </thead>
                  <tbody>
                    {card.rows.map((row, idx) => {
                      const isMatched = row.status === "matched";
                      return (
                        <tr
                          key={idx}
                          className={
                            isMatched
                              ? "kstr-row-matched"
                              : row.source === "system"
                                ? "kstr-row-system-only"
                                : "kstr-row-upload-only"
                          }
                        >
                          <td>
                            {isMatched ? (
                              <span className="kstr-reconciled-yes">
                                ✓ Reconciled
                              </span>
                            ) : (
                              <span className="kstr-reconciled-no">
                                ✗ Not Reconciled
                              </span>
                            )}
                          </td>
                          <td>{row.etr_invoice_number || "-"}</td>
                          <td>{row.name_of_purchaser || "-"}</td>
                          <td>{row.pin_of_purchaser || "-"}</td>
                          <td>{row.cu_invoice_date || "-"}</td>
                          <td className="kstr-text-right">
                            {row.taxable_value != null
                              ? Number(row.taxable_value).toLocaleString(
                                  "en-KE",
                                  {
                                    maximumFractionDigits: 2,
                                  },
                                )
                              : "-"}
                          </td>
                          <td>{row.invoice_name || "-"}</td>
                        </tr>
                      );
                    })}
                    {card.rows.length === 0 && (
                      <tr>
                        <td colSpan={7}>
                          <span className="kstr-empty">No records</span>
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ResultsTable({
  rows,
  showReconciled = false,
  emptyMessage = "No records found.",
}) {
  if (!rows.length) {
    return <div className="kstr-empty-state">{emptyMessage}</div>;
  }

  const showStatusCol = showReconciled;

  return (
    <div className="kstr-table-wrap">
      <table className="kstr-table">
        <thead>
          <tr>
            {showStatusCol ? <th>Reconciled</th> : <th>Status</th>}
            {COLUMNS.map((c) => (
              <th key={c.key} className={c.numeric ? "kstr-text-right" : ""}>
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => {
            const meta = STATUS_META[row.status] || {};
            return (
              <tr key={idx} className={meta.rowClass || ""}>
                <td>
                  {showStatusCol ? (
                    row.status === "matched" ? (
                      <span className="kstr-reconciled-yes">✓ Reconciled</span>
                    ) : (
                      <span className="kstr-reconciled-no">
                        ✗ Not Reconciled
                      </span>
                    )
                  ) : (
                    <span
                      className={`kstr-status-badge ${meta.badgeClass || ""}`}
                    >
                      {meta.label || row.status}
                    </span>
                  )}
                </td>
                <td>{row.etr_invoice_number || "-"}</td>
                <td>{row.name_of_purchaser || "-"}</td>
                <td>{row.pin_of_purchaser || "-"}</td>
                <td>{row.cu_invoice_date || "-"}</td>
                <td className="kstr-text-right">
                  {row.taxable_value != null
                    ? Number(row.taxable_value).toLocaleString("en-KE", {
                        maximumFractionDigits: 2,
                      })
                    : "-"}
                </td>
                <td>{row.invoice_name || "-"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

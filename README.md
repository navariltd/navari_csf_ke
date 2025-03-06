# ERPNext Country Specific Functionality for Kenya (CSF_KE)

_*Enhancing ERPNext with Kenya-specific features for tax compliance, payroll, and localized business needs.*_
---

## Overview

This is a custom application designed to extend the capabilities of [ERPNext](https://erpnext.com/) to meet the unique regulatory and operational requirements of businesses in Kenya. Developed by [Navari Limited](https://navari.co.ke), this app provides seamless integration with Kenyan tax systems, localized payroll reporting, and additional tools tailored to streamline business processes.

Key features include:
- Tax compliance with Kenya Revenue Authority (KRA) regulations.
- Integration with TIMs (Tax Invoice Management System).
- Comprehensive payroll reports for statutory deductions.
- Localized financial and tax reporting.

This README provides an overview of the application, its features, installation instructions, and additional resources to get you started.

---
 
## Features

### 1. Kenya Payroll Reports
Designed to ensure compliance with Kenyan payroll regulations, these reports generate the necessary documentation for statutory deductions and employee payments.

- **[P9A Tax Deduction Card Setup](csf_ke/docs/features/P9A_tax_deduction_card_setup.md)**  
  Explains the process of mapping salary components
- **[P9A Tax Deduction Card](csf_ke/docs/reports/kenya_p9_tax_report.md) Report**  
  Summarizes annual Pay As You Earn (PAYE) tax deductions for employees, required for tax filing.
- **[P10 Tax Report](csf_ke/docs/reports/kenya_p10_tax_report.md)**  
  Monthly tax return report submitted by employers to KRA.
- **NSSF Report**  
  Tracks contributions to the National Social Security Fund (NSSF) for employee social security.
- **NHIF Report**  
  Details contributions to the National Hospital Insurance Fund (NHIF) for health insurance.
- **HELB Report**  
  Summarizes deductions for Higher Education Loans Board (HELB) repayments.
- **Bank Payroll Advice Report**  
  Generates bank-ready instructions for salary disbursements.
- **Payroll Register Report**  
  Provides a detailed breakdown of payroll transactions for record-keeping and auditing.

### 2. Tax Reports
Streamlined reporting for sales and purchase taxes to ensure compliance with Kenyan tax laws.

- **[Sales Tax Report](csf_ke/docs/reports/kenya_sales_tax_report.md)**  
  Summarizes VAT and other taxes collected from sales transactions.
- **[Purchase Tax Report](csf_ke/docs/reports/kenya_purchase_tax_report.md)**  
  Details VAT and taxes paid on purchases for accurate tax reconciliation.

### 3. Tax Compliance Features
Custom fields and integrations to meet KRA tax regulations and facilitate seamless reporting.

- **Custom ETR Fields in Invoices**  
  Captures TIMs invoice details in Sales and Purchase Invoices for Electronic Tax Register (ETR) compliance.
- **TIMs HSCode Integration**  
  Links items to Harmonized System (HS) codes for accurate tax classification and reporting.  
  *[Learn more](csf_ke/docs/features/tims_integration.md)*.
- **[VAT Withholding](csf_ke/docs/doctypes/vat_withholding.md)**  
  Simplifies importing VAT withholding data from the KRA website into ERPNext for reconciliation.

#### TIMs Parser Integration
For TIMs integration, we partner with [Cecypo](https://docs.cecypo.tech/s/kb/doc/erpnext-O7U5xeE9DN). Contact them for installation and setup assistance.

### 4. Additional Features
- **[Selling Item Price Margin](csf_ke/docs/doctypes/selling_item_price_margin.md)**  
  Calculates and tracks profit margins on sales items to aid in pricing and profitability analysis.

---


## Installation 🛠️

Follow the instructions below to install CSF_KE on your ERPNext instance. You can choose between self-hosting with Frappe Bench or using FrappeCloud.

### Prerequisites
- A working ERPNext instance (v13 or higher recommended).
- Access to a terminal with `bench` commands enabled (for self-hosting).
- Git installed on your system.

### Option 1: Manual Installation (Self-Hosting)
1. **Set Up Frappe Bench**  
   If you don’t already have a Frappe Bench instance, follow the [official Frappe installation guide](https://frappeframework.com/docs/user/en/installation) to set it up.

2. **Add the CSF_KE App**  
   In your Bench directory, run the following command to download the app from GitHub:
   ```sh
   bench get-app https://github.com/navariltd/navari_csf_ke.git
   ```

3. **Install the App on Your Site**
    Replace `<your.site.name.here>` with your ERPNext site name and run:
    ```sh
    bench --site <your.site.name.here> install-app csf_ke
    ```

4. **Verify Installation**

    Restart your Bench instance and log in to ERPNext to confirm that the `CSF_KE` app appears in your app list.

---

### Option 2: FrappeCloud Installation ☁️

1. **Set Up a FrappeCloud Account**
   Sign up or log in to [FrappeCloud](https://frappecloud.com/).

2. Create a Bench and Site
   Follow the FrappeCloud dashboard instructions to create a new Bench and site.

3. Add the CSF_KE App
   - Navigate to the **Apps** tab in your Bench.
   - Click **Add App**.
   - Search  **Navari CSF Ke**
   - Click **Install**.
   OR
   - [Frappe Cloud Marketplace](https://frappecloud.com/marketplace/apps/csf_ke)
   - Click **Install Now**.

4. Activate the App
- Once installed in your bench, add the app on your site via the FrappeCloud interface.

---

## Configuration

After installation, configure the app to suit your business needs:

1. Set Up Tax Rules
- Define VAT, set up P9A Tax Deduction, and withholding tax settings in ERPNext’s **Accounts** module.

2. Link TIMs Integration
- Contact [Cecypo](mailto:support@cecypo.tech) for TIMs Parser setup.

### Test Reports
- Run sample payroll and tax reports to ensure data accuracy.
- Make some transactions to ensure TIMs Tax fields are setup.
---

## Usage Examples

### Generating a P9A Tax Deduction Card
1. Navigate to the **Kenya** module in ERPNext.
2. Select **P9A Tax Deduction Card Report** from the Payroll reports.
3. Choose the **employee** and **year**.
4. Export the report as a **PDF** for submission to KRA or employee records.

### Importing Customer's Paid VAT Withholding Data
1. Log in to the **KRA portal** and download your VAT withholding statement.
2. In ERPNext, go to the **VAT Withholding** doctype and click **Import**.
3. Upload the file using the **Data Import** tool and map the fields as prompted.
4. Save and Submit the imported records and reconcile the **Journal Entries** created.

### Selling Item Price Margins
1. Open the **Selling Item Price Margin** doctype.
2. Set up your preferred **Price List**, **Margin Type**, **Margin Amount** and **Items**
3. **Save** and **Submit** the newly created document.
4. The system automatically calculates the **margin percentage** for analysis on Purchase Receipt or Purchase Invoice submission.

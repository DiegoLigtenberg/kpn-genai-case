AI Engineer Take-Home Assignment:
Invoice Processing System
Overview
Build a lightweight AI-powered solution that processes invoices to extract structured information,
categorize expenses, and automatically approve or reject them based on predefined business
rules.
This is a prototype assignment. We value clear thinking and good engineering trade-offs over
completeness.
Background
Finance teams receive invoices in various formats (digital PDFs, scanned images, email
attachments). Currently, someone manually reviews each invoice, extracts key details, assigns
categories, and decides whether to approve or reject based on company policy.
Your task is to automate this workflow while maintaining auditability and transparency in
decision-making.
Your Task
Build an end-to-end solution that:
• Ingests invoices (PDF and images support)
• Extracts structured fields from each invoice
• Categorizes invoices into expense categories
• Applies approval guidelines to produce ACCEPT/REJECT decisions with clear
explanations
• Outputs results in machine-readable JSON format
• Provides a simple interface (CLI, or minimal web app)
Required Deliverables
A link to [GitHub] repository containing the pipeline code that processes invoices end-to-end.
Technical Requirements
Input Data
Use the invoices provided in the email.
Extracted Fields
Your solution must extract all information you deem essential for the invoice solution.
Approval Guidelines
Implement the following deterministic rules (no "model decides"):
1. Reject if total_amount > €500
2. Reject if invoice_date < 2017
3. Reject if any required field is missing (vendor, invoice_date, buyer’s name, total_amount)
4. Reject if sum(items.line_total) differs from total_amount by more than €1.00 (tolerance
for rounding)
5. Reject if individual item_amount > €200
6. Reject if the same invoice is submitted more than once
7. Accept otherwise
Store approval rules and thresholds in a configuration file. The decision engine must be auditable:
each REJECT must include specific reasons tied to which rule(s) failed.
Questions
If you have questions about the assignment:
You can send an email to finanalytics [finanalytics@kpn.com] or Bas Bollaart
[basbollaart@kpn.com].
Good luck! We look forward to seeing your solution.
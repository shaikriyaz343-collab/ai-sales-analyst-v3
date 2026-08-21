# Report hardening — v3.2

The uploaded `My Business_business_report.pdf` exposed several production UX/content issues.

## Fixed
- Report coverage now shows **source fields** rather than canonical analysis fields.
- Empty/semantically recognized dimensions are not rendered as empty headings.
- Ranked dimension breakdowns such as Regions and Payment Methods are rendered when data exists.
- The compatibility-only Transactional Sales pack no longer creates an orphan report heading.
- Estimated return amount is explicitly labelled and includes its calculation basis.
- Small-sample concentration findings explicitly say they are based on the uploaded sample and are directional.
- Report generation is covered by regression tests.

For the supplied Retail sample, the source file is 6 rows × 11 source fields; normalization adds one internal analysis field. The report now correctly reports 11 source fields.

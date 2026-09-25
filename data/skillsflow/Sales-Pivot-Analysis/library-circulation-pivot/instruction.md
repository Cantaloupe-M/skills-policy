Read the book catalog from `/root/book_catalog.pdf` and the circulation records from `/root/circulation_records.xlsx`, then create a new report called `/root/circulation_report.xlsx`.

The book catalog PDF contains columns: BOOK_ID, TITLE, GENRE, AUTHOR, YEAR_PUBLISHED.
The circulation records XLSX contains columns: LOAN_ID, BOOK_ID, BORROWER_TYPE, LOAN_DATE, RETURN_DATE (dates are in ISO format YYYY-MM-DD).

Before building pivots, reconcile the data:
- Trim whitespace in BOOK_ID and BORROWER_TYPE.
- Drop rows where BOOK_ID is missing or not found in the catalog.
- Drop rows where LOAN_DATE or RETURN_DATE is missing or RETURN_DATE is not after LOAN_DATE.
- Remove exact duplicate circulation rows after cleanup.

Join the two datasets on BOOK_ID. Then create a new Excel file with four pivot table sheets and one source data sheet (five sheets total):

1. "Loans by Genre"
This sheet contains a pivot table with:
Rows: GENRE
Values: Count (number of loan records)

2. "Avg Duration by Genre"
This sheet contains a pivot table with:
Rows: GENRE
Values: Average of LOAN_DURATION (see SourceData enrichment below)

3. "Loans by Borrower Type"
This sheet contains a pivot table with:
Rows: BORROWER_TYPE
Values: Count (number of loan records)

4. "Genre Borrower Matrix"
This sheet contains a pivot table with:
Rows: GENRE
Columns: BORROWER_TYPE
Values: Count (number of loan records)

5. "SourceData"
This sheet contains the cleaned, joined data enriched with:
- LOAN_DURATION: Number of days between RETURN_DATE and LOAN_DATE (as an integer)
- DECADE: The decade of publication derived from YEAR_PUBLISHED. Use the format "1990s", "2000s", "2010s", "2020s", etc.
- RETURN_STATUS: `returned` for every retained row
- WEEKDAY_BUCKET: `weekend` if LOAN_DATE falls on a Saturday or Sunday, otherwise `weekday`

Save the final results in `/root/circulation_report.xlsx`

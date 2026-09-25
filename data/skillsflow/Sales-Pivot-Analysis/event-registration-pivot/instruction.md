Read the event catalog from `/root/event_catalog.pdf`, online registrations from `/root/online_registrations.xlsx`, and walk-in registrations from `/root/walkin_registrations.csv`. Then create a consolidated registration report at `/root/registration_report.xlsx`.

The event catalog PDF contains columns: EVENT_ID, EVENT_NAME, TRACK, VENUE, MAX_CAPACITY.

The online registrations XLSX contains columns: REG_ID, EVENT_ID, ATTENDEE_NAME, REG_TYPE, AMOUNT_PAID.

The walk-in registrations CSV contains columns with different names but equivalent meaning:
- walk_in_id (equivalent to REG_ID)
- event_code (equivalent to EVENT_ID)
- guest_name (equivalent to ATTENDEE_NAME)
- registration_type (equivalent to REG_TYPE)
- fee_paid (equivalent to AMOUNT_PAID)

You must align the walk-in CSV columns to match the online XLSX column names, then combine both registration sources into a single dataset. After combining, join with the event catalog on EVENT_ID. Any registrations referencing event IDs not found in the catalog should be dropped during the join.

Create a new Excel file with four pivot table sheets and one source data sheet (five sheets total):

1. "Revenue by Track"
This sheet contains a pivot table with:
Rows: TRACK
Values: Sum of AMOUNT_PAID

2. "Attendance by Venue"
This sheet contains a pivot table with:
Rows: VENUE
Values: Count (number of registration records)

3. "Track RegType Matrix"
This sheet contains a pivot table with:
Rows: TRACK
Columns: REG_TYPE
Values: Sum of AMOUNT_PAID

4. "Events by Track"
This sheet contains a pivot table with:
Rows: TRACK
Values: Count (number of registration records)

5. "SourceData"
This sheet contains the combined and joined data enriched with:
- SOURCE: "Online" for records from the XLSX file, "Walk-in" for records from the CSV file
- IS_VIP: "Yes" if REG_TYPE is "VIP", otherwise "No"
- PRICE_TIER: Based on AMOUNT_PAID:
  - "Free" if AMOUNT_PAID <= 0
  - "Budget" if 0 < AMOUNT_PAID <= 100
  - "Standard" if 100 < AMOUNT_PAID <= 200
  - "Premium" if AMOUNT_PAID > 200

Save the final results in `/root/registration_report.xlsx`

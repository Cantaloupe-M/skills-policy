Read the student roster from `/root/student_roster.pdf` and course grades from `/root/course_grades.xlsx`, then create a new report called `/root/student_performance_report.xlsx`.

The student roster PDF contains columns: STUDENT_ID, STUDENT_NAME, DEPARTMENT, ENROLLMENT_YEAR.
The course grades XLSX contains columns: STUDENT_ID, COURSE_NAME, SEMESTER, SCORE, CREDITS.

Before building pivots, reconcile the data:
- Trim whitespace and standardize SEMESTER casing (e.g., "Fall 2023" rather than "fall 2023").
- Drop rows where STUDENT_ID is missing or does not match a roster entry.
- Remove exact duplicate grade rows after cleanup.

Join the two datasets on STUDENT_ID. Then create a new Excel file with four pivot table sheets and one source data sheet (five sheets total):

1. "Avg Score by Department"
This sheet contains a pivot table with:
Rows: DEPARTMENT
Values: Average of SCORE

2. "Students by Department"
This sheet contains a pivot table with:
Rows: DEPARTMENT
Values: Count (number of grade records)

3. "Credits by Semester"
This sheet contains a pivot table with:
Rows: SEMESTER
Values: Sum of CREDITS

4. "Department Semester Matrix"
This sheet contains a pivot table with:
Rows: DEPARTMENT
Columns: SEMESTER
Values: Average of SCORE

5. "SourceData"
This sheet contains the cleaned, joined data enriched with:
- GRADE_BAND: Assign each record a band based on SCORE:
  - "A" for SCORE >= 90
  - "B" for 80 <= SCORE < 90
  - "C" for 70 <= SCORE < 80
  - "D" for 60 <= SCORE < 70
  - "F" for SCORE < 60
- WEIGHTED_SCORE: SCORE × CREDITS
- TERM_STATUS: "summer_intensive" if the SEMESTER name contains "Summer", otherwise "standard"
- RETAKE_FLAG: "Yes" if SCORE < 70, otherwise "No"

Save the final results in `/root/student_performance_report.xlsx`

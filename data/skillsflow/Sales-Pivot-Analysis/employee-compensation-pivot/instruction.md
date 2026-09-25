Read the department directory from `/root/departments.pdf` and employee compensation data from `/root/employee_compensation.csv`, then create a new report called `/root/compensation_report.xlsx`.

The department PDF contains columns: DEPT_CODE, DEPT_NAME, LOCATION, ANNUAL_BUDGET.
The employee CSV contains columns: emp_id, full_name, department_code, job_title, base_salary, annual_bonus, years_of_service, hire_year.

Join the two datasets by matching the CSV's `department_code` column with the PDF's `DEPT_CODE` column. Then create a new Excel file with four pivot table sheets and one source data sheet (five sheets total):

1. "Avg Salary by Department"
This sheet contains a pivot table with:
Rows: DEPT_NAME
Values: Average of base_salary

2. "Headcount by Location"
This sheet contains a pivot table with:
Rows: LOCATION
Values: Count (number of employees)

3. "Total Compensation by Title"
This sheet contains a pivot table with:
Rows: job_title
Values: Sum of TOTAL_COMP (see SourceData enrichment below)

4. "Department Location Matrix"
This sheet contains a pivot table with:
Rows: DEPT_NAME
Columns: job_title
Values: Average of base_salary

5. "SourceData"
This sheet contains the joined data enriched with:
- TOTAL_COMP: base_salary + annual_bonus
- EXPERIENCE_BAND: Assign based on years_of_service:
  - "Junior" for years_of_service < 3
  - "Mid" for 3 <= years_of_service < 8
  - "Senior" for 8 <= years_of_service < 15
  - "Veteran" for years_of_service >= 15
- COMP_RATIO: TOTAL_COMP / ANNUAL_BUDGET (the employee's total compensation as a fraction of their department's annual budget)

Save the final results in `/root/compensation_report.xlsx`

import os
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s')

def compute_salary(base_salary_path, attendance_path, deductions_path, working_days=30, filter_date_range=None):
    """
    Compute salary given base salary, attendance, and deduction Excel file paths.

    :param base_salary_path: Path to base salary Excel file
    :param attendance_path: Path to attendance Excel file
    :param deductions_path: Path to deductions Excel file
    :param working_days: Number of working days in the pay period (default 30)
    :param filter_date_range: Optional tuple (start_date, end_date) to filter attendance by date (as 'YYYY-MM-DD' strings)
    :return: pd.DataFrame with salary calculations
    """
    # Load dataframes
    base_salary_df = pd.read_excel(base_salary_path)
    attendance_df = pd.read_excel(attendance_path)
    deductions_df = pd.read_excel(deductions_path)

    # Validate required columns
    required_base_columns = {'Employee_ID', 'Employee_Name', 'Base_Salary'}
    required_attendance_columns = {'Employee_ID', 'Date', 'Status'}
    required_deductions_columns = {'Employee_ID', 'Advance', 'Goods', 'Other_Expenses'}

    if not required_base_columns.issubset(base_salary_df.columns):
        raise ValueError(f"Base salary file missing columns: {required_base_columns - set(base_salary_df.columns)}")
    if not required_attendance_columns.issubset(attendance_df.columns):
        raise ValueError(f"Attendance file missing columns: {required_attendance_columns - set(attendance_df.columns)}")
    if not required_deductions_columns.issubset(deductions_df.columns):
        raise ValueError(f"Deductions file missing columns: {required_deductions_columns - set(deductions_df.columns)}")

    # Optionally filter attendance by date range if provided
    if filter_date_range:
        start_date, end_date = filter_date_range
        attendance_df['Date'] = pd.to_datetime(attendance_df['Date'])
        attendance_df = attendance_df[(attendance_df['Date'] >= start_date) & (attendance_df['Date'] <= end_date)]
        logging.info(f"Filtered attendance between {start_date} and {end_date}")

    # Calculate attendance summary (count of 'Present')
    attendance_summary = attendance_df[attendance_df['Status'] == 'Present'].groupby('Employee_ID').size().reset_index(name='Days_Present')

    # Compute attendance factor
    attendance_summary['Attendance_Factor'] = attendance_summary['Days_Present'] / working_days

    # Merge and fill missing values
    merged = pd.merge(base_salary_df, attendance_summary, on='Employee_ID', how='left').fillna({'Days_Present': 0, 'Attendance_Factor': 0})
    merged = pd.merge(merged, deductions_df, on='Employee_ID', how='left').fillna({'Advance': 0, 'Goods': 0, 'Other_Expenses': 0})

    # Compute salaries
    merged['Gross_Salary'] = merged['Base_Salary'] * merged['Attendance_Factor']
    merged['Total_Deductions'] = merged[['Advance', 'Goods', 'Other_Expenses']].sum(axis=1)
    merged['Net_Salary'] = merged['Gross_Salary'] - merged['Total_Deductions']

    # Select relevant columns
    result_df = merged[['Employee_ID', 'Employee_Name', 'Gross_Salary', 'Total_Deductions', 'Net_Salary']]

    logging.info("Salary computation completed successfully")

    return result_df

if __name__ == "__main__":
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'uploads'))

    base_salary_file = os.path.join(base_path, 'base_salary.xlsx')
    attendance_file = os.path.join(base_path, 'attendance.xlsx')
    deductions_file = os.path.join(base_path, 'deductions.xlsx')

    try:
        # Uncomment and set date range for filtering attendance if required
        # filter_dates = ('2025-08-01', '2025-08-31')
        # result = compute_salary(base_salary_file, attendance_file, deductions_file, working_days=30, filter_date_range=filter_dates)

        result = compute_salary(base_salary_file, attendance_file, deductions_file)
        print(result)
        result.to_excel(os.path.join(base_path, 'calculated_salaries.xlsx'), index=False)
    except Exception as e:
        logging.error(f"Failed to compute salary: {e}")

import pandas as pd

def compute_salary(base_salary_path, attendance_path, deductions_path):
    """
    Reads base salary, attendance, and deductions Excel files,
    processes salary based on attendance and deductions,
    returns a DataFrame ready for export.
    """

    # Load Excel sheets into DataFrames
    base_salary_df = pd.read_excel(base_salary_path)
    attendance_df = pd.read_excel(attendance_path)
    deductions_df = pd.read_excel(deductions_path)

    # Expected schemas (example):
    # base_salary_df columns: ['Employee_ID', 'Employee_Name', 'Base_Salary']
    # attendance_df columns: ['Employee_ID', 'Date', 'Status'] 
    # deductions_df columns: ['Employee_ID', 'Advance', 'Goods', 'Other_Expenses']

    # Calculate total attendance days per employee (considering 'Status' could be 'Present')
    attendance_summary = attendance_df[attendance_df['Status'] == 'Present'].groupby('Employee_ID').size().reset_index(name='Days_Present')

    # Assuming salary is for full month with 30 working days - pro-rate salary
    attendance_summary['Attendance_Factor'] = attendance_summary['Days_Present'] / 30

    # Merge base salary with attendance
    merged = pd.merge(base_salary_df, attendance_summary, on='Employee_ID', how='left').fillna({'Days_Present': 0, 'Attendance_Factor': 0})

    # Merge deductions
    merged = pd.merge(merged, deductions_df, on='Employee_ID', how='left').fillna({'Advance': 0, 'Goods': 0, 'Other_Expenses': 0})

    # Compute Salary after deduction and attendance adjustment
    merged['Gross_Salary'] = merged['Base_Salary'] * merged['Attendance_Factor']
    merged['Total_Deductions'] = merged[['Advance', 'Goods', 'Other_Expenses']].sum(axis=1)
    merged['Net_Salary'] = merged['Gross_Salary'] - merged['Total_Deductions']

    # Select relevant columns for export
    result_df = merged[['Employee_ID', 'Employee_Name', 'Gross_Salary', 'Total_Deductions', 'Net_Salary']]

    return result_df

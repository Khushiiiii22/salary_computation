from openpyxl import Workbook

def export_to_tally_excel(df, output_path):
    """
    Converts the processed salary DataFrame into Excel format
    compatible with Tally import. Tally often expects specific columns
    like Ledger Name, Amount, Particulars, etc. Adjust per Tally requirement.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Salary Voucher"

    # Define headers based on typical Tally format (example)
    headers = ['Employee_ID', 'Employee_Name', 'Amount (Net Salary)', 'Deductions', 'Gross Salary']
    ws.append(headers)

    for _, row in df.iterrows():
        ws.append([
            row['Employee_ID'],
            row['Employee_Name'],
            round(row['Net_Salary'], 2),
            round(row['Total_Deductions'], 2),
            round(row['Gross_Salary'], 2)
        ])

    wb.save(output_path)

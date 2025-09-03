import os
from flask import Flask, render_template, request, url_for, redirect
from werkzeug.utils import secure_filename
from salary_processor import compute_salary
from tally_export import export_to_tally_excel

# Supabase imports
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables for Supabase
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'xlsx'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def upload():
    error = None

    if request.method == 'POST':
        # Get uploaded files
        files = {
            'base_salary_file': request.files.get('base_salary_file'),
            'attendance_file': request.files.get('attendance_file'),
            'deductions_file': request.files.get('deductions_file'),
        }
        # Get payroll period dates from form
        pay_period_start = request.form.get('pay_period_start')
        pay_period_end = request.form.get('pay_period_end')

        # Validate payroll period dates
        if not pay_period_start or not pay_period_end:
            error = "Payroll period start and end dates are required."
        else:
            from datetime import datetime
            try:
                pay_period_start_date = datetime.strptime(pay_period_start, '%Y-%m-%d').date()
                pay_period_end_date = datetime.strptime(pay_period_end, '%Y-%m-%d').date()
            except ValueError:
                error = "Payroll period dates must be valid dates in YYYY-MM-DD format."

        # Validate files
        if not error:
            for key, file in files.items():
                if not file or file.filename == '':
                    error = f"Missing file: {key.replace('_', ' ').title()}"
                    break
                if not allowed_file(file.filename):
                    error = f"Invalid file type for {key.replace('_', ' ').title()}"
                    break

        if not error:
            saved_paths = {}
            try:
                # Save uploaded files
                for key, file in files.items():
                    filename = secure_filename(file.filename)
                    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(path)
                    saved_paths[key] = path

                # Compute salary DataFrame with filtered attendance by payroll period
                salary_df = compute_salary(
                    base_salary_path=saved_paths['base_salary_file'],
                    attendance_path=saved_paths['attendance_file'],
                    deductions_path=saved_paths['deductions_file'],
                    filter_date_range=(pay_period_start, pay_period_end)
                )

                # Insert salary rows into Supabase with payroll period info
                for _, row in salary_df.iterrows():
                    data = {
                        "employee_id": row['Employee_ID'],
                        "employee_name": row['Employee_Name'],
                        "gross_salary": float(row['Gross_Salary']),
                        "total_deductions": float(row['Total_Deductions']),
                        "net_salary": float(row['Net_Salary']),
                        "pay_period_start": pay_period_start,
                        "pay_period_end": pay_period_end
                    }
                    supabase.table("salaries").insert(data).execute()

                # Export to Tally Excel
                output_filename = "salary_tally_import.xlsx"
                output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
                export_to_tally_excel(salary_df, output_path)

                # Store saved file paths in app config for salary_result route if needed
                app.config['LAST_SAVED_PATHS'] = saved_paths

                return redirect(url_for('salary_result'))

            except Exception as e:
                error = f"Processing error: {str(e)}"

    return render_template('upload.html', title="Salary Computation Service", error=error)

@app.route('/salary_result')
def salary_result():
    # Query latest 100 salary records from Supabase, ordered by ID descending
    query = supabase.table("salaries").select("*").order("id", desc=True).limit(100).execute()
    records = query.data if query.data else []

    if not records:
        return redirect(url_for('upload'))

    import pandas as pd
    salary_df = pd.DataFrame(records)

    # Convert to HTML table with custom headers
    table_html = salary_df[['employee_id', 'employee_name', 'gross_salary', 'total_deductions', 'net_salary', 'pay_period_start', 'pay_period_end']].to_html(
        classes='table table-striped', index=False,
        header=["Employee ID", "Employee Name", "Gross Salary", "Total Deductions", "Net Salary", "Period Start", "Period End"]
    )

    return render_template('salary_result.html', table_html=table_html)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
from salary_processor import compute_salary
from tally_export import export_to_tally_excel

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
    output_url = None

    if request.method == 'POST':
        files = {
            'base_salary_file': request.files.get('base_salary_file'),
            'attendance_file': request.files.get('attendance_file'),
            'deductions_file': request.files.get('deductions_file'),
        }

        # Validate files presence and extensions
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
                for key, file in files.items():
                    filename = secure_filename(file.filename)
                    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(path)
                    saved_paths[key] = path

                # Compute salary, returns a pandas DataFrame
                salary_df = compute_salary(
                    base_salary_path=saved_paths['base_salary_file'],
                    attendance_path=saved_paths['attendance_file'],
                    deductions_path=saved_paths['deductions_file']
                )

                # Export to Tally format Excel
                output_filename = "salary_tally_import.xlsx"
                output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
                export_to_tally_excel(salary_df, output_path)

                output_url = url_for('download_file', filename=output_filename)

            except Exception as e:
                error = f"Processing error: {str(e)}"

    return render_template('upload.html', title="Salary Computation Service", error=error, output_url=output_url)

@app.route('/outputs/<filename>')
def download_file(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)

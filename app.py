import os
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from datetime import datetime  # Add this with other imports
from PyPDF2 import PdfReader
from plagiarism_detector import check_plagiarism_online, check_plagiarism_offline

app = Flask(__name__)

# Configuration for file storage
UPLOAD_FOLDER = 'stored_pdfs'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/store_files', methods=['POST'])
def store_files():
    """Stores uploaded PDFs in the upload folder."""
    files = request.files.getlist('files')
    if not files:
        return jsonify({'message': 'No files uploaded'})

    stored_files = []
    for file in files:
        if file.filename.endswith('.pdf'):
            # Save file to disk
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            stored_files.append(filename)

    return jsonify({
        'message': f'{len(stored_files)} PDFs stored successfully for comparison',
        'stored_files': stored_files
    })

@app.route('/check_offline', methods=['POST'])
@app.route('/check_offline', methods=['POST'])
def check_offline():
    """Checks the uploaded PDF against stored PDFs."""
    try:
        file = request.files.get('file')
        if not file or not file.filename.endswith('.pdf'):
            return jsonify({'error': 'Invalid or missing PDF file'}), 400

        # Create upload folder if it doesn't exist
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)

        # Save the uploaded file temporarily with a unique name
        temp_filename = secure_filename(f"temp_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
        temp_path = os.path.join(UPLOAD_FOLDER, temp_filename)
        file.save(temp_path)

        # Extract text from the uploaded file
        reader = PdfReader(temp_path)
        input_text = ''.join([page.extract_text() or '' for page in reader.pages])

        # Get list of stored files (excluding our temp file)
        stored_files = [f for f in os.listdir(UPLOAD_FOLDER) 
                       if f.endswith('.pdf') and f != temp_filename]
        
        if not stored_files:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return jsonify({'message': 'No stored files available for comparison'})

        # Call plagiarism detection
        results = check_plagiarism_offline(input_text, UPLOAD_FOLDER, stored_files)

        # Clean up the temporary file if it exists
        if os.path.exists(temp_path):
            os.remove(temp_path)
            if results['copied']:
                return jsonify({
                'copied': True,
                'percentage_copied': float(results.get('percentage_copied', 0)),
                'results': [{
                'file': source.get('file', ''),
                'string_match': float(source.get('string_match', 0)),
                'cosine_similarity': float(source.get('cosine_similarity', 0)),
                'time_taken_string_match': float(source.get('time_taken_string_match', 0)),
                'time_taken_cosine': float(source.get('time_taken_cosine', 0)),
                'copied_text': source.get('copied_text', '')
            } for source in results.get('sources', [])],
            'detailed_copied_texts': [{
                'file': source.get('file', ''),
                'copied_text': source.get('copied_text', '')
            } for source in results.get('sources', [])]
        })
        return jsonify({
        'copied': False,
        'message': "No matching sources found.",
        'percentage_copied': 0,
        'results': [],
        'detailed_copied_texts': []
        })
     
    except Exception as e:
        # Ensure we clean up temp file even if error occurs
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({'error': str(e)}), 500

@app.route('/check_online', methods=['POST'])
def check_online():
    """Performs online plagiarism detection."""
    text = request.form.get('text', '')
    upload_file = request.files.get('file')

    # If a file is uploaded, extract text from the PDF
    if upload_file:
        filename = secure_filename(upload_file.filename)
        upload_file.save(filename)  # Save temporarily
        extracted_text = extract_text_from_pdf(filename)  #
        os.remove(filename)  # Remove temporary file
    else:
        extracted_text = text 
    # Check plagiarism using online sources
    online_results = check_plagiarism_online(extracted_text)
    online_results['extracted_text'] = extracted_text 
    return jsonify(online_results)

def extract_text_from_pdf(file_path):
    """Extracts text from a PDF file."""
    try:
        reader = PdfReader(file_path)
        text = ''.join([page.extract_text() or '' for page in reader.pages])
        return text
    except Exception as e:
        return ''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

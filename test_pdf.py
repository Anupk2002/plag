from PyPDF2 import PdfReader

def extract_text_from_pdf(file_path):
    try:
        reader = PdfReader(file_path)
        text = ''
        for page in reader.pages:
            page_text = page.extract_text() or ''
            text += page_text
        print(f"Extracted Text: {text[:100]}...")  # Print the first 100 characters
        return text
    except Exception as e:
        print(f"Error extracting text: {e}")

if __name__ == "__main__":
    pdf_path = "D:\\Soham\\Documents\\copy.pdf"  # Replace with the actual path to a PDF file
    extract_text_from_pdf(pdf_path)

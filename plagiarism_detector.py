
import os
import re
import time
import difflib
import requests
from PyPDF2 import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize
from difflib import SequenceMatcher
import nltk
nltk.download('punkt')
nltk.download('stopwords')


def check_plagiarism_online(input_text):
    api_key = 'AIzaSyCqvaeUTAlnmS6OE07aofH7a5VvfWwXu2U'
    engine_id = '46e309481c1b4431f'

    search_url = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={engine_id}&q={input_text}"
    print(f"Searching for: {input_text[:]}...")
    response = requests.get(search_url)

    results = response.json()
    print(f"API Response: {results}")

    matches = []
    copied = False
    total_length = 0

    if 'items' in results:
        for item in results['items']:
            copied = True
            snippet = item['snippet']
            matches.append({
                'matching_text': snippet,
                'source': item['link']
            })
            total_length += len(snippet)

    percentage_copied = (total_length / len(input_text)) * 100 if len(input_text) > 0 else 0

    return {
        'copied': copied,
        'sources': matches,
        'percentage_copied': min(percentage_copied, 100)
    }


def clean_text(text):
    return re.sub(r'\s+', ' ', text).strip()


def lcs_length(text1, text2, min_length=20):
    m = len(text1)
    n = len(text2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m):
        for j in range(n):
            if text1[i] == text2[j]:
                dp[i + 1][j + 1] = dp[i][j] + 1
            else:
                dp[i + 1][j + 1] = max(dp[i + 1][j], dp[i][j + 1])
    return dp[m][n]


def cosine_similarity(text1, text2):
  try:
    stop_words = stopwords.words('english')
    tfidf_vectorizer = TfidfVectorizer(stop_words=stop_words)
    tfidf_matrix = tfidf_vectorizer.fit_transform([text1, text2])
    cosine_sim = (tfidf_matrix * tfidf_matrix.T).toarray()[0, 1]
    return cosine_sim * 100
  except:
    return 0.0

def extract_text_from_pdf(file_path):
    reader = PdfReader(file_path)
    text = ''
    for page in reader.pages:
        text += page.extract_text() or ''
    return text


def sentence_level_similarity(text1, text2, threshold=0.6):
    sentences1 = sent_tokenize(text1)
    sentences2 = sent_tokenize(text2)
    similar_sentences = []

    for s1 in sentences1:
        for s2 in sentences2:
            ratio = SequenceMatcher(None, s1, s2).ratio()
            if ratio >= threshold:
                similar_sentences.append({
                    'input_sentence': s1,
                    'matched_sentence': s2,
                    'similarity': round(ratio * 100, 2)
                })
    return similar_sentences


def paragraph_level_similarity(text1, text2, threshold=0.5):
    paragraphs1 = [p.strip() for p in text1.split('\n') if len(p.strip()) > 30]
    paragraphs2 = [p.strip() for p in text2.split('\n') if len(p.strip()) > 30]
    matched_paragraphs = []

    for p1 in paragraphs1:
        for p2 in paragraphs2:
            ratio = SequenceMatcher(None, p1, p2).ratio()
            if ratio >= threshold:
                matched_paragraphs.append({
                    'input_paragraph': p1,
                    'matched_paragraph': p2,
                    'similarity': round(ratio * 100, 2)
                })

    return matched_paragraphs


def deep_structure_match_analysis(input_text, source_text):
    cleaned_input = clean_text(input_text)
    cleaned_source = clean_text(source_text)

    sentence_matches = sentence_level_similarity(cleaned_input, cleaned_source)
    paragraph_matches = paragraph_level_similarity(cleaned_input, cleaned_source)

    return {
        'sentence_level_matches': sentence_matches,
        'paragraph_level_matches': paragraph_matches
    }


def check_plagiarism_offline(input_text,upload_folder, stored_files):
    best_match_file = None
    best_match_segments = []
    best_match_length = 0
    best_match_percentage = 0
    input_text_cleaned = clean_text(input_text)
    sources = []

    for filename in stored_files:
        file_path = os.path.join(upload_folder, filename)
        try:
            # Extract text from the stored PDF
            reader = PdfReader(file_path)
            pdf_text = ''.join([page.extract_text() or '' for page in reader.pages])
            pdf_text_cleaned = clean_text(pdf_text)

            matcher = difflib.SequenceMatcher(None, input_text_cleaned, pdf_text_cleaned)

            current_match_length = 0
            current_matches = []

            # Check for exact matches first
            if input_text_cleaned == pdf_text_cleaned:
                sources.append({
                    'file': filename,
                    'matches': [input_text_cleaned],
                    'string_match': 100.0,
                    'copied_text': input_text_cleaned
                })
                best_match_file = filename
                best_match_length = len(input_text_cleaned)
                best_match_percentage = 100.0
                best_match_segments = [input_text_cleaned]
                continue

            # Find matching blocks
            for match in matcher.get_matching_blocks():
                if match.size > 10:  # Only consider matches longer than 10 characters
                    matching_text = pdf_text_cleaned[match.b: match.b + match.size]
                    current_matches.append(matching_text)
                    current_match_length += len(matching_text)

            if current_match_length > 0:
                string_match_percentage = (current_match_length / len(input_text_cleaned)) * 100
                sources.append({
                    'file': filename,
                    'matches': current_matches,
                    'string_match': string_match_percentage,
                    'copied_text': "\n".join(current_matches)
                })

                if current_match_length > best_match_length:
                    best_match_file = filename
                    best_match_length = current_match_length
                    best_match_percentage = string_match_percentage
                    best_match_segments = current_matches

        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")
            continue

    if not sources or best_match_length == 0:
        return {
            'copied': False,
            'sources': [],
            'message': 'No copied text found'
        }

    # Calculate additional similarity metrics for the best matches
    for source in sources:
        if source['string_match'] > 10:  # Only for significant matches
            file_path = os.path.join(upload_folder, source['file'])
            reader = PdfReader(file_path)
            source_text = ''.join([page.extract_text() or '' for page in reader.pages])
            
            source['lcs'] = (lcs_length(input_text_cleaned, source_text) / len(input_text_cleaned)) * 100
            source['cosine_similarity'] = cosine_similarity(input_text_cleaned, source_text)

    overall_percentage_copied = (best_match_length / len(input_text_cleaned)) * 100

    return {
        'copied': True if best_match_length > 0 else False,
        'sources': sources,
        'percentage_copied': overall_percentage_copied,
        'total_copied_text': "\n".join(best_match_segments)
    }

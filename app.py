from flask import Flask, request, jsonify
import pickle, re
import numpy as np
from flask_cors import CORS
import traceback

import re

from textblob import TextBlob
import re, math

def evaluate_urgency(text):
    # Analyze sentiment
    blob = TextBlob(text)
    sentiment = blob.sentiment

    # Define urgency keywords
    urgency_keywords = ['urgent', 'immediately', 'as soon as possible', 'asap', 'quick', 'emergency', 'critical', 'now', 'need', 'quickly', 'fast', 'hurry']
    keyword_pattern = r'\b(?:' + '|'.join(urgency_keywords) + r')\b'

    # Check for urgency keywords
    keywords_found = re.findall(keyword_pattern, text, re.IGNORECASE)

    # Scoring based on sentiment and keywords
    score = len(keywords_found) * 10  # Assign 10 points per keyword
    if sentiment.polarity < -0.3:  # Negative sentiment
        score += 5
    if sentiment.subjectivity > 0.5:  # High subjectivity can sometimes indicate personal urgency
        score += 5

    sus = []
    if(score / math.log(len(text) + 1) > 3):
        for word in urgency_keywords:
            if word in keywords_found:
                sus.append(word)
        return [1, sus]
    return [0, sus]

def find_suspicious_links(text):
    # List of commonly safe TLDs, consider expanding this list as needed
    safe_tlds = ['.org', '.com', '.net', '.edu', '.gov', '.uk', '.de', '.jp', '.fr', '.au', '.us', '.ca', '.ch', '.it', '.nl', '.se', '.no', '.es', '.mil']
    
    # More specific Regex to find URLs with or without http(s)
    url_pattern = r'\b(?:https?://)?(?:www\.)?[a-zA-Z0-9-]{1,63}(?:\.[a-zA-Z0-9-]{1,63})+\b'
    
    # List of additional suspicious patterns in URLs
    suspicious_patterns = [
        r'@',  # Embedded credentials (username:password@)
        r'//[^/]*:',  # Colon immediately after double slashes might indicate a port number or password
        r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'  # IP address in URL
    ]
    
    # Find all URLs in the given text
    urls = re.findall(url_pattern, text)
    
    # Filter URLs that are suspicious either by pattern or by TLD
    suspicious_urls = []
    for url in urls:
        domain_part = url.split('/')[0]  # Focus on the domain part for TLD checking
        if any(re.search(pattern, url) for pattern in suspicious_patterns) or \
           not any(domain_part.endswith(tld) for tld in safe_tlds):
            suspicious_urls.append(url)
    
    return suspicious_urls

def is_asking_for_private_info(text):
    sus = []
    # Possessive pronouns that might indicate a request for private information
    possessives = ["your", "his", "her", "my", "ur"]
    
    # Data terms associated with private information
    private_data_terms = [
        "name", "phone", "number", "email", "address",
        "social security number", "ssn", "credit card", 
        "bank account", "instagram", "insta", "kakao talk", 
        "katalk", "kakaotalk", "snapchat"
    ]

    # Generate patterns dynamically
    patterns = [rf"\b{pronoun} {data_term}\b" for pronoun in possessives for data_term in private_data_terms]

    # Check if any of the patterns are found in the text
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            sus.append(pattern[2:-2])
    return sus


app = Flask(__name__)
CORS(app)

# Load the model and vectorizer
with open('classifier.pkl', 'rb') as f:
    model = pickle.load(f)

with open('vectorizer.pkl', 'rb') as f:
    vectorizer = pickle.load(f)

with open('unique_scam_words.pkl', 'rb') as f:
    unique_scam_words = pickle.load(f)

@app.route('/predict', methods=['POST'])
def predict():
    try:
        danger = []
        pred_model, pred_link, pred_info, pred_urgent = 0, 0, 0, 0
        json_data = request.get_json()
        messages = json_data['messages']
        received = []
        sent = []
        result = []
        for m in messages:
            align = m["type"]
            text = m["text"]
            if(align == "L"):
                received.append(text)
            elif(align == "R"):
                sent.append(text)        

        received_text = ""
        for message in received:
            received_text += message + " "
            message_clean = re.sub('[^a-zA-Z]', ' ', message)
            message_clean = message_clean.lower().split()
            message_clean = " ".join(message_clean)
            message_vector = vectorizer.transform([message_clean]).toarray()
            prediction = model.predict(message_vector)
            print(message, prediction[0])
            if(int(prediction[0]) == 1):
                pred_model = 1
                for m in message.split():
                    if m in unique_scam_words:
                        danger.append(m)
        
        suspicious_links = find_suspicious_links(received_text)
        if(len(suspicious_links) > 0):
            pred_link = 1
            danger.extend(suspicious_links)
        
        private_info = is_asking_for_private_info(received_text)
        if(len(private_info) > 0):
            pred_info = 1
            danger.extend(private_info)
            
        [pred_urgent, urgency_words] = evaluate_urgency(received_text)
        if(pred_urgent):
            danger.extend(urgency_words)
            
        result = (received_text, pred_model, pred_link, pred_info, pred_urgent)
    except Exception as e:
        traceback.print_exc()
        stack_trace = traceback.format_exc()
        return jsonify({"error": str(e), "trace": stack_trace}), 500

    return jsonify({"result": result, "danger": danger})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
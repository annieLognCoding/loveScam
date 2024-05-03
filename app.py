from flask import Flask, request, jsonify
import pickle, re
import numpy as np
from flask_cors import CORS
import traceback
import nltk

import re

from textblob import TextBlob
import re, math
from nltk.corpus import words
from nltk.corpus import wordnet as wn

# Ensure NLTK resources are available
nltk.download('wordnet')
nltk.download('words')

# Load the model and vectorizer
with open('classifier.pkl', 'rb') as f:
    model = pickle.load(f)

with open('vectorizer.pkl', 'rb') as f:
    vectorizer = pickle.load(f)

with open('unique_scam_words.pkl', 'rb') as f:
    unique_scam_words = pickle.load(f)
    
with open('irregular_verbs.pkl', 'rb') as f:
    irregular_verbs = pickle.load(f)


def refine_model_prediction(text, pred, danger):
    # Calculate sentiment
    sentiment = TextBlob(text).sentiment
    # Define a range for neutral sentiment
    NEUTRAL_LOWER_BOUND = -0.1
    NEUTRAL_UPPER_BOUND = 0.1    
    EXTREME_LOWER_BOUND = -0.7
    EXTREME_UPPER_BOUND = 0.7    
    # Check if the sentiment is within the neutral range
    if pred == 1 and NEUTRAL_LOWER_BOUND < sentiment.polarity < NEUTRAL_UPPER_BOUND:
        return ''

    if pred == 1 and len(text) <= 5 and set(text.split()).isdisjoint(set(danger)):
        return ''  
    
    if sentiment.polarity > EXTREME_UPPER_BOUND or sentiment.polarity < EXTREME_LOWER_BOUND or not set(text.split()).isdisjoint(set(danger)):
        return text

    return text if pred else ''

def evaluate_urgency(text):
    # Analyze sentiment
    blob = TextBlob(text)
    sentiment = blob.sentiment
    # Retrieve all verb lemmas and their forms
    # Return the first past tense form found
    # Filter for unique irregular past tense forms
    negative_irregular_verbs = set()
    for verb in list(irregular_verbs):
        blob_verb = TextBlob(verb)
        sentiment_verb = blob_verb.sentiment
        if sentiment.polarity < -0.5:
            negative_irregular_verbs.update(sentiment_verb)
    # Format for regex usage
    irregular_past_tense_regex = '|'.join(map(re.escape, set(negative_irregular_verbs)))  # Escape special characters

    # Final regex
    # Define urgency keywords
    urgency_keywords = ['urgent', 'immediately', 'as soon as possible', 'asap', 'quick', \
                        'emergency', 'critical', 'now', 'need', 'quickly', 'fast', 'hurry'\
                        'stole', 'lost', 'money', 'broke', 'right away']
    keyword_pattern = r'\b(?:' + '|'.join(urgency_keywords) + r')\b'
    delete_number = r'\bdelete\b.*?\bnumber\b'
    just_finished = f"\\bjust\\b(\\s+\\w+)?(\\s+\\w+)?\\s+(\\w+)((ed|en)|({irregular_past_tense_regex}))?\\b"

    
    
    # Check for urgency keywords
    keywords_found = re.findall(keyword_pattern, text, re.IGNORECASE)
    delete_found = re.findall(delete_number, text, re.IGNORECASE)
    just_found = re.findall(just_finished, text, re.IGNORECASE)

    # Scoring based on sentiment and keywords
    score = (len(keywords_found) + len(delete_found) + len(just_found))* 10  # Assign 10 points per keyword
    if sentiment.polarity < -0.3:  # Negative sentiment
        score += 5
    if sentiment.subjectivity > 0.5:  # High subjectivity can sometimes indicate personal urgency
        score += 5

    sus = []
    if(score / math.log(len(text) + 1) > 3):
        for word in urgency_keywords:
            if word in keywords_found:
                sus.append(word)
        if len(just_found) > 0:
            sus.append("just (urgent)")
        if len(delete_found) > 0:
            sus.append("delete number")
        return sus
    return sus

def find_suspicious_links(text):
    # List of commonly safe TLDs, consider expanding this list as needed
    safe_tlds = ['.org', '.com', '.net', '.edu', '.gov', '.uk', '.de', '.jp', '.fr', '.au', '.us', '.ca', '.ch', '.it', '.nl', '.se', '.no', '.es', '.mil']
    
    # More specific Regex to find URLs with or without http(s)
    url_pattern = r'\b(?:https?://)?(?:www\.)?[a-zA-Z0-9-]{1,63}(?:\.[a-zA-Z0-9-]{1,63})+\s*(?:/\s*[^\s]*)?\b'
    
    # List of additional suspicious patterns in URLs
    suspicious_patterns = [
        r'@',  # Embedded credentials (username:password@)
        r'//[^/]*:',  # Colon immediately after double slashes might indicate a port number or password
        r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'  # IP address in URL
    ]
    
    # Find all URLs in the given text
    urls = re.findall(url_pattern, text)
    english_words_set = set(words.words())    
    
    # Filter URLs that are suspicious either by pattern or by TLD
    suspicious_urls = []
    for url in urls:
        url_parts = url.split('/')
        domain_part = url_parts[0]
        if(len(url_parts) >= 2 and 'http' in url_parts[0]):
            domain_part = url_parts[1]
        # Focus on the domain part for TLD checking
        if any(re.search(pattern, url) for pattern in suspicious_patterns) or \
           not any(domain_part.endswith(tld) for tld in safe_tlds) \
                and False in [word.strip().lower() in english_words_set for word in url.split(".")]:
            suspicious_urls.append(url)
    
    return suspicious_urls

def is_asking_for_private_info(text):
    sus = []
    # Possessive pronouns that might indicate a request for private information
    possessives = ["your", "ur", "my"]
    
    # Data terms associated with private information
    private_data_terms = [
        "name", "number", "phone number", "email", "address",
        "social security number", "ssn", "credit card", 
        "bank account", "instagram", "insta", "kakao talk", 
        "katalk", "kakaotalk", "snapchat", "account", "password", "pw"
    ]

    # Generate patterns dynamically
    patterns = [
        r"\b{}\b(?:\s+\w+'s)?(?:\s+\w+){{0,1}}\s*{}\b[.,!?;:]*".format(pronoun, data_term)
        for pronoun in possessives for data_term in private_data_terms
    ]

    # Check if any of the patterns are found in the text
    for i in range(len(patterns)):
        pattern = patterns[i]
        if re.search(pattern, text):
            sus.append(possessives[i//len(private_data_terms)] + " " + private_data_terms[i%len(private_data_terms)])
    return sus


app = Flask(__name__)
CORS(app)



@app.route('/predict', methods=['POST'])
def predict():
    try:
        danger = []
        pred_model = 0
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
        message_pred = []
        score = 0
        for message in received:
            received_text += message + " "
            message_clean = re.sub('[^a-zA-Z]', ' ', message)
            message_clean = message_clean.lower().split()
            message_clean = " ".join(message_clean)
            message_vector = vectorizer.transform([message_clean]).toarray()
            prediction = model.predict(message_vector)
            message_pred.append([message, prediction[0]])
            if(int(prediction[0]) == 1 and len(message.split()) >= 3):
                pred_model = 1
                for m in message.split():
                    if m in unique_scam_words:
                        danger.append(m)
        print(message_pred)        
        if(pred_model and len(danger) > 0):
            danger_texts = [refine_model_prediction(message_point[0], message_point[1], danger) for message_point in message_pred]
            score += sum([len(text) for text in danger_texts]) * 1.5 
            print(danger_texts)

        suspicious_links = find_suspicious_links(received_text)
        if(len(suspicious_links) > 0):
            score += (sum([len(link) for link in suspicious_links]) / 15) * 0.1 * len(received_text)
            if(pred_model): score += 0.7 * len(received_text)
            danger.extend(suspicious_links)
        
        private_info = is_asking_for_private_info(received_text)
        if(len(private_info) > 0):
            score += (sum([len(info_word) for info_word in private_info]) / 5) * 0.1 * len(received_text)
            if(pred_model): score += 0.7 * len(received_text)
            danger.extend(private_info)
        print(score)
        print(score)
        urgency_words = evaluate_urgency(received_text)
        if(len(urgency_words) > 0):
            score += (sum([len(urgency_word) for urgency_word in urgency_words]) // 5 + 1) * (len(received_text) * 0.1)
            if(pred_model): score += 0.7 * len(received_text)
            print(score/ len(received_text))
            print(score/ len(received_text))
            danger.extend(urgency_words)
        
        blob = TextBlob(received_text)
        print(danger)
            
        score = score / len(received_text)
        if(score >= 1): score = 0.98
             
        result = (received_text, score, 1 - score)
    except Exception as e:
        traceback.print_exc()
        stack_trace = traceback.format_exc()
        return jsonify({"error": str(e), "trace": stack_trace}), 500

    return jsonify({"result": result, "danger": danger})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
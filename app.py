from flask import Flask, request, jsonify
import pickle, re
import numpy as np
from flask_cors import CORS

import re

def find_suspicious_links(text):
    safe_tlds = ['.org', '.com', '.net', '.edu']  # Default list of unsuspicious TLDs
    
    # Regex to find URLs with or without http(s)
    url_pattern = r'(?:https?://)?(?:www\.)?[-\w]+(?:\.[-\w]+)+'
    
    # List of additional suspicious patterns in URLs
    suspicious_patterns = [
        r'@',           # Embedded credentials (username:password@)
        r'//[^/]*:',    # Colon immediately after double slashes might indicate a port number or password
        r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b' # IP address in URL
    ]
    
    # Find all URLs in the given text
    urls = re.findall(url_pattern, text)
    
    # Filter URLs that are suspicious either by pattern or by TLD
    suspicious_urls = []
    for url in urls:
        if any(re.search(pattern, url) for pattern in suspicious_patterns) or \
           not any(url.endswith(tld) for tld in safe_tlds):
            suspicious_urls.append(url)
    
    return suspicious_urls


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
        pred_link, pred = 0, 0
        json_data = request.get_json()
        messages = json_data['messages']
        received = []
        sent = []
        result = {}
        for m in messages:
            align = m["type"]
            text = m["text"]
            if(align == "L"):
                received.append(text)
            elif(align == "R"):
                sent.append(text)        

        for message in received:
            message_clean = re.sub('[^a-zA-Z]', ' ', message)
            message_clean = message_clean.lower().split()
            if(len(message_clean) >= 3):
                message_clean = " ".join(message_clean)
                message_vector = vectorizer.transform([message_clean]).toarray()
                prediction = model.predict(message_vector)
                # Convert NumPy int64 to Python int
                if(int(prediction[0]) == 1):
                    for m in message.split():
                        if m in unique_scam_words:
                            danger.append(m)
                pred = int(prediction[0])
                suspicious_links = find_suspicious_links(message)
                if(len(suspicious_links) > 0):
                    pred_link = 1
                    danger.extend(suspicious_links)
            result[message] = (pred, pred_link)
    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500

    return jsonify({"result": result, "danger": danger})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
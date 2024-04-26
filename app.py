from flask import Flask, request, jsonify
import pickle, re
import numpy as np
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Load the model and vectorizer
with open('classifier.pkl', 'rb') as f:
    model = pickle.load(f)

with open('vectorizer.pkl', 'rb') as f:
    vectorizer = pickle.load(f)

@app.route('/predict', methods=['POST'])
def predict():
    try:
        json_data = request.get_json()
        message = json_data['message']
        message = re.sub('[^a-zA-Z]', ' ', message)
        message = message.lower().split()
        message = " ".join(message)
        message_vector = vectorizer.transform([message]).toarray()
        prediction = model.predict(message_vector)
        # Convert NumPy int64 to Python int
        result = int(prediction[0])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
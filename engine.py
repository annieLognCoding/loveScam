import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import re, nltk
# nltk.download()
from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer
from nltk.probability import FreqDist

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.metrics import confusion_matrix, accuracy_score
import pickle

# Assume cv is your CountVectorizer that has been fitted to the corpus

import pandas as pd
import re
from sklearn.feature_extraction.text import CountVectorizer

# Import datasets
dataset = pd.read_csv("./archive/train.csv")
dataset2 = pd.read_csv("./archive/Dataset_5971.csv")

corpus = []

# Process the first dataset
for i in range(dataset['sms'].size):
    # Replace everything that is not a letter
    message = re.sub('[^a-zA-Z]', ' ', dataset['sms'][i])
    # Convert to lowercase and split into words
    message = message.lower().split()
    # Rejoin words to form the cleaned message
    message = " ".join(message)
    corpus.append(message)

# Process the second dataset
# for i in range(dataset2['TEXT'].size):
#     # Replace everything that is not a letter
#     message = re.sub('[^a-zA-Z]', ' ', dataset2['TEXT'][i])
#     # Convert to lowercase and split into words
#     message = dataset2['TEXT'][i].lower().split()
#     # Rejoin words to form the cleaned message
#     message = " ".join(message)
#     corpus.append(message)

# Create a Bag of Words model
cv = CountVectorizer(max_features=4000)
X = cv.fit_transform(corpus).toarray()

# Prepare labels from both datasets
y = dataset['label'].tolist()  # Assuming this column contains binary labels
# y.extend([0 if label == 'ham' else 1 for label in dataset2['LABEL']])  # Extend with labels from dataset2

# Convert labels list to an array if necessary
y = np.array(y)
        

# split training set and test set

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state = 0)

#train model with Gaussian model
classifier = GaussianNB()
classifier.fit(X_train, y_train)

y_pred = classifier.predict(X_test)

cm = confusion_matrix(y_test, y_pred)
print(cm)
print(accuracy_score(y_test, y_pred))


with open('vectorizer.pkl', 'wb') as f:
    pickle.dump(cv, f)

with open('classifier.pkl', 'wb') as f:
    pickle.dump(classifier, f)

plainWords, scamWords = [], []
for i in range(dataset['sms'].size):
    if(int(dataset['label'][i]) == 0):
        plainWords.extend(dataset['sms'][i].split())
    else:
        scamWords.extend(dataset['sms'][i].split())

stop_words = set(stopwords.words('english'))

fq1 = FreqDist(token.lower() for token in plainWords if token.lower() not in stop_words)
fq2 = FreqDist(token.lower() for token in scamWords if token.lower() not in stop_words)

# Convert FreqDist keys to sets
set_fq1 = set(fq1.most_common(len(fq1)//2))
set_fq2 = set(fq2.keys())

unique_to_fq2 = []
for word in set_fq2:
    if((fq2[word] - fq1[word]) > fq2[word] * 0.2):
        unique_to_fq2.append(word)

# Find words in fq2 not in fq1
unique_to_fq2_sorted = sorted(unique_to_fq2, key=lambda x: fq2[x], reverse=True)
unique_scam_words = list(unique_to_fq2_sorted)

with open('unique_scam_words.pkl', 'wb') as f:
    pickle.dump(unique_scam_words, f)
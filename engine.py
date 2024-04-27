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

#importing dataset
dataset = pd.read_csv("./archive/train.csv")

corpus = []

#cleaning text (without stemming / stopwords cleaning)
for i in range(dataset['sms'].size):
    # replace everything that is not a letter
    message = re.sub('[^a-zA-Z]', ' ', dataset['sms'][i])    
    # capital to lowercase
    message = message.lower()
    message = message.split()
    message = " ".join(message)
    corpus.append(message)

#create a bag of words with the spam corpus
cv = CountVectorizer(max_features=4000)
X = cv.fit_transform(corpus).toarray()
y = dataset.iloc[:, -1].values

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

fq1 = FreqDist(token.lower() for token in plainWords if token not in stopwords.words('english'))
fq2 = FreqDist(token.lower() for token in scamWords if token not in stopwords.words('english'))

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
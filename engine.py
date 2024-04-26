import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import re, nltk
from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.metrics import confusion_matrix, accuracy_score
import pickle

# Assume cv is your CountVectorizer that has been fitted to the corpus

#importing dataset
dataset = pd.read_csv("./archive/train.csv")

print(dataset.size)
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
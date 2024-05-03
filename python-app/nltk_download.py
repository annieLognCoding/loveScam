import nltk

def setup_nltk_resources():
    # Download necessary NLTK resources
    nltk.download('wordnet')
    nltk.download('words')
    print("NLTK resources downloaded successfully.")

if __name__ == "__main__":
    setup_nltk_resources()
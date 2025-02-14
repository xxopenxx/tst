import ujson
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
import joblib
from typing import List, Dict, Tuple

def load_data(fp: str) -> List[Dict]:
    with open(fp, 'r') as f:
        return ujson.load(f)
    
def prepare_data(data: List[Dict]) -> Tuple[List, List]:
    texts = [item['query'] for item in data]
    labels = [item['routed_to'] for item in data]
    return texts, labels

def train_and_save_model(texts, labels, model_path):
    X_train, X_test, y_train, y_test = train_test_split(texts, labels, test_size=0.2, random_state=42)
    
    model = Pipeline([
        ('tfidf', TfidfVectorizer()),
        ('clf', MultinomialNB())
    ])
    
    model.fit(X_train, y_train)
    
    accuracy = model.score(X_test, y_test)
    print(f"Model accuracy: {accuracy:.2f}")

    joblib.dump(model, model_path)

def main():
    data = load_data('ai/router_llm/data/training.json')
    texts, labels = prepare_data(data)
    train_and_save_model(texts, labels, 'text_classifier_model.pkl')

if __name__ == '__main__':
    main()
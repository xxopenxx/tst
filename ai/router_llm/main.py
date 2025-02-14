import joblib
import sys

def load_model(model_path):
    return joblib.load(model_path)

def predict(query, model):
    prediction = model.predict([query])
    return prediction[0]

def main(query):
    model = load_model('text_classifier_model.pkl')
    domain = predict(query, model)
    print(f"The domain for the query is: {domain}")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python predict.py 'Your query here'")
        sys.exit(1)
    
    query = sys.argv[1]
    main(query)

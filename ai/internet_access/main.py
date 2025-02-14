import torch
import torch.nn as nn
from transformers import BertTokenizer, BertModel
import torch.nn.functional as F
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.tag import pos_tag
from nltk.chunk import ne_chunk
from sklearn.feature_extraction.text import TfidfVectorizer
from concurrent.futures import ThreadPoolExecutor
from aiocache import cached, SimpleMemoryCache

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')

class InternetClassifier(nn.Module):
    def __init__(self, dropout=0.5):
        super(InternetClassifier, self).__init__()
        self.bert = BertModel.from_pretrained('bert-base-uncased')
        self.dropout = nn.Dropout(dropout)
        self.linear = nn.Linear(768, 2)

    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        pooled_output = outputs[1]
        dropout_output = self.dropout(pooled_output)
        return self.linear(dropout_output)

model = InternetClassifier().to(device)
model.load_state_dict(torch.load('ai/internet_access/data/internet_classifier.pth', map_location=device))
model.eval()

stop_words = set(stopwords.words('english')) - {'how', 'what', 'why', 'when', 'where', 'who'}
important_pos = {'NN', 'NNS', 'NNP', 'NNPS', 'VB', 'VBD', 'VBG', 'VBN', 'VBP', 'VBZ', 'JJ', 'JJR', 'JJS'}

@cached(ttl=60, cache=SimpleMemoryCache)
async def cached_extract_named_entities(text):
    chunks = ne_chunk(pos_tag(word_tokenize(text)))
    entities = []
    for chunk in chunks:
        if hasattr(chunk, 'label'):
            entities.append(' '.join(c[0] for c in chunk))
    return entities

@cached(ttl=60, cache=SimpleMemoryCache)
async def cached_tfidf_importance(query):
    tfidf_vectorizer = TfidfVectorizer(stop_words=list(stop_words))
    corpus = [query, ' '.join(stop_words)]
    X = tfidf_vectorizer.fit_transform(corpus)
    feature_names = tfidf_vectorizer.get_feature_names_out()
    tfidf_scores = X.toarray()[0]
    return dict(zip(feature_names, tfidf_scores))

class QueryOptimizer:
    def __init__(self):
        self.executor = ThreadPoolExecutor()

    async def extract_named_entities(self, text):
        return await cached_extract_named_entities(text)

    async def tfidf_importance(self, query):
        return await cached_tfidf_importance(query)
    
    async def optimize_query(self, query, max_length=100):
        entities = await self.extract_named_entities(query)
        tokens = word_tokenize(query)
        tagged = pos_tag(tokens)
        tfidf_scores = await self.tfidf_importance(query)
        
        question_words = {'how', 'what', 'why', 'when', 'where', 'who'}
        optimized_query_parts = []
        
        for word, tag in tagged:
            lower_word = word.lower()
            if (lower_word in question_words or 
                tag in important_pos or 
                word in entities or 
                word.isdigit() or 
                lower_word not in stop_words):
                optimized_query_parts.append(word)
        
        optimized_query = ' '.join(optimized_query_parts)
        
        if len(optimized_query) > max_length:
            optimized_query = optimized_query[:max_length].rsplit(' ', 1)[0]
        
        return optimized_query

def predict_internet_need(text, threshold=0.7):
    encoding = tokenizer.encode_plus(
        text,
        add_special_tokens=True,
        max_length=128,
        return_token_type_ids=False,
        padding='max_length',
        truncation=True,
        return_attention_mask=True,
        return_tensors='pt',
    )
    input_ids = encoding['input_ids'].to(device)
    attention_mask = encoding['attention_mask'].to(device)

    with torch.no_grad():
        outputs = model(input_ids, attention_mask)
        probabilities = F.softmax(outputs, dim=1)
        confidence, predicted_class = torch.max(probabilities, dim=1)
        
    confidence = confidence.item()
    needs_internet = bool(predicted_class.item())
    
    if confidence < threshold:
        return True, confidence, "Uncertain"  # uncertain, so return True
    else:
        return needs_internet, confidence, "Certain"

if __name__ == "__main__":
    import time
    print("Enter prompts to test. Type 'exit' to quit.")
    while True:
        prompt = input("Enter a prompt: ")
        if prompt.lower() == 'exit':
            break
        
        start = time.time()
        
        result, confidence, certainty = predict_internet_need(prompt)
        print(f"Needs Internet: {result}")
        print(f"Confidence: {confidence:.4f}")
        print(f"Certainty: {certainty}")
        print(f"time taken: {round(time.time() - start, 2)}")
        print()

import multiprocessing
from functools import lru_cache
from textblob import TextBlob
from sklearn.feature_extraction.text import TfidfVectorizer
from nltk.corpus import stopwords
import nltk

nltk.download('stopwords', quiet=True)
nltk.download('punkt', quiet=True)


class QueryOptimizer:
    def __init__(self):
        self.stop_words = set(stopwords.words('english')) - {'how', 'what', 'why', 'when', 'where', 'who'}
        self.important_pos = {'NN', 'VB', 'JJ', 'NNP'}
        self.tfidf_vectorizer = TfidfVectorizer(stop_words=list(self.stop_words))
        self.pool = multiprocessing.Pool(processes=multiprocessing.cpu_count())

    @lru_cache(maxsize=1000)
    def process_query(self, query):
        blob = TextBlob(query)
        entities = [word for word, tag in blob.tags if tag.startswith('NNP')]
        tokens = [word for word, tag in blob.tags if
                  tag[:2] in self.important_pos or word.lower() not in self.stop_words]
        return entities, tokens

    @lru_cache(maxsize=1000)
    def tfidf_importance(self, query):
        corpus = [query, ' '.join(self.stop_words)]
        X = self.tfidf_vectorizer.fit_transform(corpus)
        feature_names = self.tfidf_vectorizer.get_feature_names_out()
        tfidf_scores = X.toarray()[0]
        return dict(zip(feature_names, tfidf_scores))

    def optimize_query(self, query, max_length=120):
        if '?' in query and any(query.lower().startswith(q) for q in ['how', 'what', 'why', 'when', 'where', 'who']):
            return query

        if len(query.split()) <= 3:
            keywords = [word for word in TextBlob(query).words if word.lower() not in self.stop_words]
            return f"What about {' '.join(keywords)}?"

        entities, tokens = self.process_query(query)
        tfidf_scores = self.tfidf_importance(query)

        optimized_query_parts = [
            token for token in tokens
            if token in entities or token.lower() not in self.stop_words
        ]

        optimized_query_parts = sorted(
            optimized_query_parts,
            key=lambda x: tfidf_scores.get(x.lower(), 0),
            reverse=True
        )

        optimized_query = ' '.join(optimized_query_parts)

        if len(optimized_query) > max_length:
            optimized_query = optimized_query[:max_length].rsplit(' ', 1)[0]

        optimized_query = optimized_query.rstrip(".?") + '?'
        return optimized_query[0].upper() + optimized_query[1:]


if __name__ == "__main__":
    optimizer = QueryOptimizer()
    query = "how can i meow?"
    optimized_query = optimizer.optimize_query(query)
    print(optimized_query)

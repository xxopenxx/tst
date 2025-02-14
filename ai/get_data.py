import requests
import ujson
import re
import time
import random

groq_api = 'Bearer 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'
organization = ""

# Load the model data
model_data = ujson.load(open("data/models/list.json", 'r'))

# Extract model names
model_names = [model["id"] for model in model_data["data"]]

sys_template = f"""You are an AI expert who creates datasets for training LLM routers.
Your objective is to generate a dataset of diverse queries along with the appropriate LLM to route them to.

Generate 50+ examples of queries with their corresponding routing decisions.

Here are some example responses:
[
    {{"query": "What is the capital of France?", "complexity": "low", "domain": "general", "response_time": "fast", "routed_to": "gemma-2b"}},
    {{"query": "Explain quantum entanglement in detail", "complexity": "high", "domain": "physics", "response_time": "standard", "routed_to": "claude-3.5-sonnet"}}
]

Rules:
- Responses should be in JSON format and cover a wide range of query types and domains.
- Generate about 50 examples.
- REMEMBER, RESPOND IN JSON.
- DO NOT INDENT/FORMAT THE JSON. Use the format: [{{}}]
- Include the query, complexity level, domain, response time requirement, and the LLM it should be routed to.

Complexity levels: low, medium, high
Domains: general, medical, legal, scientific, technical, creative, language, business, etc.
Response times: fast, standard
LLMs: {', '.join(model_names)}

Vary the examples to create a diverse dataset that covers different scenarios a router might encounter.
"""

def llm_request(messages):
    headers = {
        'accept': 'application/json',
        'accept-language': 'en-US,en;q=0.9',
        'authorization': groq_api,
        'content-type': 'application/json',
        'groq-app': 'chat',
        'groq-organization': organization,
        'origin': 'https://groq.com',
        'priority': 'u=1, i',
        'referer': 'https://groq.com/',
        'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }

    payload = {
        'model': 'mixtral-8x7b-32768',
        'messages': messages,
        'temperature': 0.2,
        'max_tokens': 32768,
        'top_p': 1,
        'stream': False,
    }

    try:
        res = requests.post('https://api.groq.com/openai/v1/chat/completions', headers=headers, json=payload)
        res.raise_for_status()
        return res.json()['choices'][0]['message']['content']
    except requests.exceptions.RequestException as e:
        print(f"Error in API request: {e}")
        return None

def generate_dataset():
    system = sys_template
    request = llm_request(messages=[
        {'role': 'user', 'content': system},
    ])

    if request:
        struc = re.search(r'\[.*\]', request, re.DOTALL).group(0)
        dataset = ujson.loads(struc)
        return dataset
    else:
        return None

training_data = []

def create_training_data():
    while True:
        try:
            dataset = generate_dataset()
            print("Processing: LLM router training data")
            if dataset is not None:
                print(f"Generated {len(dataset)} examples")
                training_data.extend(dataset)

                with open('llm_router_training_data.json', 'w') as f:
                    ujson.dump(training_data, f, indent=4)

                print(f"Total training data: {len(training_data)}")
            else:
                print("Failed to generate dataset")
            
            time.sleep(random.uniform(15, 20))
        except Exception as e:
            print(f"An error occurred: {e}")

create_training_data()
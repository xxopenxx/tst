from curl_cffi import requests

cookies = {
    'sessionId': '268413e2-7e65-4abc-9cb5-fad095ec4ecd',
    'intercom-id-x55eda6t': '57c0e670-ce78-450e-8190-5094f1e0aeb3',
    'intercom-session-x55eda6t': '',
    'intercom-device-id-x55eda6t': 'f0006645-e904-44f2-b45a-18f84a305dc0',
    'render_session_affinity': 'e57bc3bb-b32e-4103-a6f5-063616388059',
    '__Host-authjs.csrf-token': '45d91791fc5c887a0c80f360685b430936d1ff0a963eddaa879fd44f28f02e01%7C67a10045510a89ede8bf7dde5881bae3a84e07eca5796cee7ba196c4602f1b9a',
    '__Secure-authjs.callback-url': 'https%3A%2F%2Fwww.blackbox.ai',
    'perf_dv6Tr4n': '1',
}

headers = {
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.9',
    'content-type': 'application/json',
    # 'cookie': 'sessionId=268413e2-7e65-4abc-9cb5-fad095ec4ecd; intercom-id-x55eda6t=57c0e670-ce78-450e-8190-5094f1e0aeb3; intercom-session-x55eda6t=; intercom-device-id-x55eda6t=f0006645-e904-44f2-b45a-18f84a305dc0; render_session_affinity=e57bc3bb-b32e-4103-a6f5-063616388059; __Host-authjs.csrf-token=45d91791fc5c887a0c80f360685b430936d1ff0a963eddaa879fd44f28f02e01%7C67a10045510a89ede8bf7dde5881bae3a84e07eca5796cee7ba196c4602f1b9a; __Secure-authjs.callback-url=https%3A%2F%2Fwww.blackbox.ai; perf_dv6Tr4n=1',
    'origin': 'https://www.blackbox.ai',
    'priority': 'u=1, i',
    'referer': 'https://www.blackbox.ai/',
    'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
}

json_data = {
    'messages': [
        {
            'id': 'jtYy5WL',
            'content': '@GPT-4o what model are you',
            'role': 'user',
        },
    ],
    'agentMode': {},
    'id': 'jtYy5WL',
    'previewToken': None,
    'userId': None,
    'codeModelMode': True,
    'trendingAgentMode': {},
    'isMicMode': False,
    'userSystemPrompt': None,
    'maxTokens': 1024,
    'playgroundTopP': None,
    'playgroundTemperature': None,
    'isChromeExt': False,
    'githubToken': '',
    'clickedAnswer2': False,
    'clickedAnswer3': False,
    'clickedForceWebSearch': False,
    'visitFromDelta': False,
    'isMemoryEnabled': False,
    'mobileClient': False,
    'userSelectedModel': None,
    'validated': '00f37b34-a166-4efb-bce5-1312d87f2f94',

}

while True:
    response = requests.post('https://www.blackbox.ai/api/chat', impersonate="chrome107", cookies=cookies, headers=headers, json=json_data, proxy="http://shrdprux1s-rotate:Banssuiteonset1@p.webshare.io:80")
    print(response.text)
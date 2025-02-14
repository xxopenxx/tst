class ChatBaseProvider:
    def __init__(self, module_name, stream: bool, models: list, working: bool, limit: int = None):
        self.module_name = module_name
        self.stream = stream
        self.models = models
        self.working = working
        self.limit = limit

    async def generate_completion(self, data: dict):
        pass
    
    async def generate(self, data: dict, stream: bool, user: str):
        raise NotImplementedError("Providers must implement the `generate` method.")
    
    def check(self, data):
        return True
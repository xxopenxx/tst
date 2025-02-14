class AudioBaseProvider:
    def __init__(self, module_name, working: bool, models: list):
        self.module_name = module_name
        self.models = models
        self.working = working

    async def generate(self, data: dict):
        raise NotImplementedError("Providers must implement the `generate` method.")
    
    def check(self, data):
        return True
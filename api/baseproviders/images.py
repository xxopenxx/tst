class ImagesBaseProvider:
    def __init__(self, module_name, working: bool, models: list):
        self.module_name = module_name
        self.models = models
        self.working = working

    async def generate(self, data: dict) -> tuple[str, str]:
        """Generates an image based on the inputted data

        Args:
            data (dict): A dictionary of parameters to use to generate the image

        Returns:
            tuple[str, str]: Returns the repsonse (base64 or url) and the response type (base64 or url)
        """
        raise NotImplementedError("Providers must implement the `generate` method.")
    
    def check(self, data):
        return True
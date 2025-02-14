import asyncio
import time
from typing import List, Dict, Any, Optional
from faster_whisper import WhisperModel

models = {
    "whisper-tiny": "tiny",
    "whisper-small": "small",
    "whisper-medium": "medium",
    "whisper-base": "base",
    "whisper-tiny.en": "tiny.en"
}

class WhisperTranscriber:
    def __init__(self, device="cpu", compute_type="int8"):
        self.device = device
        self.compute_type = compute_type
        self.models = {"tiny": WhisperModel("tiny", device=device, compute_type=compute_type)}

    async def transcribe_audio(
        self,
        file_path: str,
        model_size: str = "whisper-tiny",
        beam_size: int = 5,
        timestamp_granularities: Optional[List[str]] = None,
        response_format: str = "json",
        temperature: float = 0
    ) -> Dict[str, Any]:

        model_name = models[model_size] 

        if model_name not in self.models:
            self.models[model_name] = WhisperModel(model_name, device=self.device, compute_type=self.compute_type)

        model = self.models[model_name]

        # run in a different thread to prevent blocking
        segments, info = await asyncio.to_thread(
            model.transcribe, file_path, beam_size=beam_size, word_timestamps=True, temperature=temperature
        )

        full_text = " ".join(segment.text for segment in segments)

        result = {
            "task": "transcribe",
            "language": info.language,
            "duration": info.duration,
            "text": full_text,
        }

        if timestamp_granularities is None or "segment" in timestamp_granularities:
            result["segments"] = [
                {
                    "id": i,
                    "seek": 0,
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text,
                    "tokens": segment.tokens,
                    "temperature": 0.0,
                    "avg_logprob": segment.avg_logprob,
                    "compression_ratio": 1.2363636493682861,  # placeholder bc idk what it is
                    "no_speech_prob": 0.00985979475080967  # placeholder
                }
                for i, segment in enumerate(segments)
            ]

        if timestamp_granularities is not None and "word" in timestamp_granularities:
            result["words"] = [
                {
                    "word": word.word,
                    "start": word.start,
                    "end": word.end
                }
                for segment in segments
                for word in segment.words
            ]

        if response_format == "verbose_json":
            return result
        elif response_format == "json":
            return {"text": full_text}
        elif response_format == "text":
            return full_text

        return full_text
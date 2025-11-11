from __future__ import annotations
import google.generativeai as genai

class GeminiClient:
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-pro"):
        if not api_key:
            raise ValueError("GOOGLE_API_KEY no configurada")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    def generate_json(self, prompt: str) -> str:
        resp = self.model.generate_content(prompt)
        return (resp.text or "").strip()
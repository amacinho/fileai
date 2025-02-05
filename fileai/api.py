import os
import logging
from abc import ABC, abstractmethod
from google import genai
from google.genai import types
from fileai.rate_limiter import RateLimiter
from fileai.config import load_config, save_config, FOLDERS
from pydantic import BaseModel
import json
import enum
import mimetypes
from fileai.document_handlers import get_handler
from pathlib import Path

# Dynamically create Folder enum from config
Folder = enum.Enum(
    'Folder',
    {name: name for name, _ in FOLDERS}
)
    
class Response(BaseModel):
    doc_type: str
    doc_date: str
    doc_topic: str
    doc_owner: str
    doc_folder: str  # Changed from Folder to str since Gemini expects simple types
    doc_keywords: list[str]

    def model_post_init(self, __context):
        # Validate that the folder value is valid
        if not hasattr(Folder, self.doc_folder):
            raise ValueError(f"Invalid folder value: {self.doc_folder}")
        # Keep it as string since we need the name, not the enum value

class LLMAPI(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def get_response(self, prompt:str, path: Path) -> dict:
        pass

    def get_model_name(self):
        return self.__class__.__name__

class GeminiAPI(LLMAPI):
    def __init__(self, api_key=None, model=None):
        """Initialize GeminiAPI with optional API key and model.
        
        Args:
            api_key (str, optional): Gemini API key. If not provided, will try to load from config.
            model (str, optional): Gemini model name. If not provided, will try to load from config.
        """
        super().__init__()
        
        # Load configuration
        config = load_config()
        
        # API key precedence: constructor arg > config file > environment variable
        self.api_key = api_key or config.get('api_key')
        if not self.api_key:
            raise Exception(
                "Gemini API key is required. You can provide it in one of these ways:\n"
                "1. Pass it directly: GeminiAPI(api_key='your-key')\n"
                "2. Set it in ~/.config/fileai/config.json: {\"api_key\": \"your-key\"}\n"
                "3. Set GEMINI_API_KEY environment variable"
            )
        
        # Initialize client
        self.client = genai.Client(api_key=self.api_key)
        
        # Model name precedence: constructor arg > config file > environment variable > default
        self.model_name = model or config.get('model') or "gemini-pro-vision"
        
        # Save configuration if new values were provided
        if api_key or model:
            new_config = config.copy()
            if api_key:
                new_config['api_key'] = api_key
            if model:
                new_config['model'] = model
            try:
                save_config(new_config)
            except Exception as e:
                logging.warning(f"Could not save configuration: {e}")

        self.rate_limiter = RateLimiter(max_calls=14, time_window=60)

    def _upload(self, path: Path) -> types.Content:
        file_upload = self.client.files.upload(path=path)
        return types.Content(
            role="user",
            parts=[
                types.Part.from_uri(
                    file_uri=file_upload.uri, mime_type=mimetypes.guess_type(str(path))[0]
                )
            ],
        )

    def _prepare_contents(self, prompt, path: Path) -> list[types.Content]:
        upload_content = self._upload(path=path)
        prompt_content = types.Content(role="user", parts=[types.Part.from_text(prompt)])
        return [upload_content, prompt_content]

    def get_response(self, prompt: str, path: Path) -> dict:
        contents = self._prepare_contents(prompt, path)
        self.rate_limiter.wait_if_needed()
        try:
            # Define the response schema explicitly
            schema = {
                "type": "object",
                "properties": {
                    "doc_type": {"type": "string"},
                    "doc_date": {"type": "string"},
                    "doc_topic": {"type": "string"},
                    "doc_owner": {"type": "string"},
                    "doc_folder": {"type": "string", "enum": [f.name for f in Folder]},
                    "doc_keywords": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["doc_type", "doc_date", "doc_topic", "doc_owner", "doc_folder", "doc_keywords"]
            }
            
            response = self.client.models.generate_content(
                model=self.model_name, contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )
            return json.loads(response.text)
        except Exception as err:
            raise Exception(f"Gemini API error: {str(err)}")
            

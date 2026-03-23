"""
LLM wrapper for OpenAI and Anthropic APIs.
"""
import json
import logging
from typing import Dict, Any, Optional, Union
from pydantic import BaseModel

try:
    import openai
except ImportError:
    openai = None

try:
    import anthropic
except ImportError:
    anthropic = None

from .config import get_settings

logger = logging.getLogger(__name__)


class LLMResponse(BaseModel):
    """Standardized LLM response format."""
    content: str
    usage: Optional[Dict[str, Any]] = None
    provider: str


class LLMClient:
    """Unified client for OpenAI and Anthropic APIs."""
    
    def __init__(self):
        self.settings = get_settings()
        self._openai_client = None
        self._anthropic_client = None
        
        # Initialize clients based on available API keys
        if self.settings.openai_api_key:
            if openai is None:
                logger.warning("OpenAI package not installed, but API key is available")
            else:
                self._openai_client = openai.OpenAI(
                    api_key=self.settings.openai_api_key
                )
        
        if self.settings.anthropic_api_key:
            if anthropic is None:
                logger.warning("Anthropic package not installed, but API key is available")
            else:
                self._anthropic_client = anthropic.Anthropic(
                    api_key=self.settings.anthropic_api_key
                )
    
    def _call_openai(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        """Call OpenAI API."""
        if not self._openai_client:
            raise ValueError("OpenAI client not initialized")
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self._openai_client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=self.settings.llm_temperature,
            max_tokens=self.settings.llm_max_tokens
        )
        
        return LLMResponse(
            content=response.choices[0].message.content,
            usage=response.usage.model_dump() if response.usage else None,
            provider="openai"
        )
    
    def _call_anthropic(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        """Call Anthropic API."""
        if not self._anthropic_client:
            raise ValueError("Anthropic client not initialized")
        
        messages = [{"role": "user", "content": prompt}]
        
        response = self._anthropic_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=self.settings.llm_max_tokens,
            temperature=self.settings.llm_temperature,
            system=system_prompt or "",
            messages=messages
        )
        
        return LLMResponse(
            content=response.content[0].text,
            usage=response.usage.model_dump() if hasattr(response, 'usage') else None,
            provider="anthropic"
        )
    
    def generate_response(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        provider: Optional[str] = None
    ) -> LLMResponse:
        """Generate a response using the specified or default LLM provider."""
        
        if provider is None:
            provider = self.settings.default_llm_provider
        
        try:
            if provider == "openai" and self._openai_client:
                return self._call_openai(prompt, system_prompt)
            elif provider == "anthropic" and self._anthropic_client:
                return self._call_anthropic(prompt, system_prompt)
            else:
                # Fallback to available provider
                if self._openai_client:
                    return self._call_openai(prompt, system_prompt)
                elif self._anthropic_client:
                    return self._call_anthropic(prompt, system_prompt)
                else:
                    raise ValueError("No LLM provider available")
        
        except Exception as e:
            logger.error(f"Error calling LLM provider {provider}: {str(e)}")
            raise
    
    def generate_structured_output(
        self, 
        prompt: str, 
        schema: Union[Dict[str, Any], BaseModel], 
        system_prompt: Optional[str] = None,
        provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate structured JSON output conforming to a schema."""
        
        # Prepare the structured prompt
        if isinstance(schema, type) and issubclass(schema, BaseModel):
            schema_dict = schema.model_json_schema()
        else:
            schema_dict = schema
        
        structured_prompt = f"""
{prompt}

Respond with valid JSON that matches this schema:
{json.dumps(schema_dict, indent=2)}

Important: Your response must be valid JSON only, no additional text.
"""
        
        if system_prompt is None:
            system_prompt = """You are an AI assistant that provides structured responses in JSON format. 
Always respond with valid JSON that matches the requested schema exactly."""
        
        response = self.generate_response(structured_prompt, system_prompt, provider)
        
        try:
            return json.loads(response.content.strip())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {response.content}")
            raise ValueError(f"LLM did not return valid JSON: {str(e)}")


# Global LLM client instance
llm_client = LLMClient()


def get_llm_client() -> LLMClient:
    """Get the global LLM client instance."""
    return llm_client


# Convenience functions
def generate_response(prompt: str, system_prompt: Optional[str] = None) -> str:
    """Generate a simple text response."""
    response = llm_client.generate_response(prompt, system_prompt)
    return response.content


def generate_structured_output(
    prompt: str, 
    schema: Union[Dict[str, Any], BaseModel], 
    system_prompt: Optional[str] = None
) -> Dict[str, Any]:
    """Generate structured JSON output."""
    return llm_client.generate_structured_output(prompt, schema, system_prompt)
from typing import List, Optional, Dict, Tuple, Any, Protocol, runtime_checkable
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class ModelProvider(Enum):
    """Enum for supported model providers."""
    OLLAMA = "ollama"
    GEMINI = "gemini"


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for LLM providers."""
    
    def chat(self, model: str, messages: List[Dict[str, str]], options: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """Send a chat request to the LLM provider."""
        ...

class Location(BaseModel):
    """Location information for JSON Resume format."""
    address: Optional[str] = None
    postalCode: Optional[str] = None
    city: Optional[str] = None
    countryCode: Optional[str] = None
    region: Optional[str] = None

class Profile(BaseModel):
    """Social profile information for JSON Resume format."""
    network: Optional[str] = None
    username: Optional[str] = None
    url: str

class Basics(BaseModel):
    """Basic information for JSON Resume format."""
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    url: Optional[str] = None
    summary: Optional[str] = None
    location: Optional[Location] = None
    profiles: Optional[List[Profile]] = None

class Work(BaseModel):
    """Work experience for JSON Resume format."""
    name: Optional[str] = None
    position: Optional[str] = None
    url: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    summary: Optional[str] = None
    highlights: Optional[List[str]] = None

class Volunteer(BaseModel):
    """Volunteer experience for JSON Resume format."""
    organization: Optional[str] = None
    position: Optional[str] = None
    url: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    summary: Optional[str] = None
    highlights: Optional[List[str]] = None

class Education(BaseModel):
    """Education information for JSON Resume format."""
    institution: Optional[str] = None
    url: Optional[str] = None
    area: Optional[str] = None
    studyType: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    score: Optional[str] = None
    courses: Optional[List[str]] = None

class Award(BaseModel):
    """Award information for JSON Resume format."""
    title: Optional[str] = None
    date: Optional[str] = None
    awarder: Optional[str] = None
    summary: Optional[str] = None

class Certificate(BaseModel):
    """Certificate information for JSON Resume format."""
    name: Optional[str] = None
    date: Optional[str] = None
    issuer: Optional[str] = None
    url: Optional[str] = None

class Publication(BaseModel):
    """Publication information for JSON Resume format."""
    name: Optional[str] = None
    publisher: Optional[str] = None
    releaseDate: Optional[str] = None
    url: Optional[str] = None
    summary: Optional[str] = None

class Skill(BaseModel):
    """Skill information for JSON Resume format."""
    name: Optional[str] = None
    level: Optional[str] = None
    keywords: Optional[List[str]] = None

class Language(BaseModel):
    """Language information for JSON Resume format."""
    language: Optional[str] = None
    fluency: Optional[str] = None

class Interest(BaseModel):
    """Interest information for JSON Resume format."""
    name: Optional[str] = None
    keywords: Optional[List[str]] = None

class Reference(BaseModel):
    """Reference information for JSON Resume format."""
    name: Optional[str] = None
    reference: Optional[str] = None

class Project(BaseModel):
    """Project information for JSON Resume format."""
    name: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    description: Optional[str] = None
    highlights: Optional[List[str]] = None
    url: Optional[str] = None
    technologies: Optional[List[str]] = None
    skills: Optional[List[str]] = None

class BasicsSection(BaseModel):
    """Basics section containing basic information."""
    basics: Optional[Basics] = None

class WorkSection(BaseModel):
    """Work section containing a list of work experiences."""
    work: Optional[List[Work]] = None

class EducationSection(BaseModel):
    """Education section containing a list of education entries."""
    education: Optional[List[Education]] = None

class SkillsSection(BaseModel):
    """Skills section containing a list of skill categories."""
    skills: Optional[List[Skill]] = None

class ProjectsSection(BaseModel):
    """Projects section containing a list of projects."""
    projects: Optional[List[Project]] = None

class AwardsSection(BaseModel):
    """Awards section containing a list of awards."""
    awards: Optional[List[Award]] = None
    
class JSONResume(BaseModel):
    """Complete JSON Resume format model."""
    basics: Optional[Basics] = None
    work: Optional[List[Work]] = None
    volunteer: Optional[List[Volunteer]] = None
    education: Optional[List[Education]] = None
    awards: Optional[List[Award]] = None
    certificates: Optional[List[Certificate]] = None
    publications: Optional[List[Publication]] = None
    skills: Optional[List[Skill]] = None
    languages: Optional[List[Language]] = None
    interests: Optional[List[Interest]] = None
    references: Optional[List[Reference]] = None
    projects: Optional[List[Project]] = None

class CategoryScore(BaseModel):
    score: float = Field(ge=0, description="Score achieved in this category")
    max: int = Field(gt=0, description="Maximum possible score")
    evidence: str = Field(min_length=1, description="Evidence supporting the score")

class Scores(BaseModel):
    open_source: CategoryScore
    self_projects: CategoryScore
    production: CategoryScore
    technical_skills: CategoryScore

class BonusPoints(BaseModel):
    total: float = Field(ge=0, le=20, description="Total bonus points")
    breakdown: str = Field(description="Breakdown of bonus points")

class Deductions(BaseModel):
    total: float = Field(ge=0, description="Total deduction points (stored as positive, applied as negative)")
    reasons: str = Field(description="Reasons for deductions")

class EvaluationData(BaseModel):
    scores: Scores
    bonus_points: BonusPoints
    deductions: Deductions
    key_strengths: List[str] = Field(min_items=1, max_items=5)
    areas_for_improvement: List[str] = Field(min_items=1, max_items=3)

class GitHubProfile(BaseModel):
    """Pydantic model for GitHub profile data."""
    username: str
    name: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    company: Optional[str] = None
    public_repos: Optional[int] = None
    followers: Optional[int] = None
    following: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    avatar_url: Optional[str] = None
    blog: Optional[str] = None
    twitter_username: Optional[str] = None
    hireable: Optional[bool] = None


class OllamaProvider:
    """Ollama LLM provider implementation."""
    
    def __init__(self):
        import ollama
        self.client = ollama
    
    def chat(self, model: str, messages: List[Dict[str, str]], options: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """Send a chat request to Ollama."""
        chat_params = {
            'model': model,
            'messages': messages,
            'options': options or {}
        }
        
        if 'format' in kwargs:
            chat_params['format'] = kwargs['format']
            
        return self.client.chat(**chat_params)


class GeminiProvider:
    """Google Gemini API provider implementation using Google GenAI SDK."""
    
    def __init__(self, api_key: str, safety_level: str = "professional"):
        from google import genai
        from google.genai import types
        
        # Validate API key
        if not api_key:
            raise ValueError("API key is required for GeminiProvider. Please set GEMINI_API_KEY or GOOGLE_API_KEY environment variable.")
        
        # Create client with API key
        self.client = genai.Client(api_key=api_key)
        
        # Configure safety settings based on use case
        if safety_level == "professional":
            # Moderate safety for professional resume evaluation
            self.safety_settings = [
                types.SafetySetting(
                    category='HARM_CATEGORY_HATE_SPEECH',
                    threshold='BLOCK_MEDIUM_AND_ABOVE'
                ),
                types.SafetySetting(
                    category='HARM_CATEGORY_HARASSMENT',
                    threshold='BLOCK_MEDIUM_AND_ABOVE'
                ),
                types.SafetySetting(
                    category='HARM_CATEGORY_SEXUALLY_EXPLICIT',
                    threshold='BLOCK_MEDIUM_AND_ABOVE'
                ),
                types.SafetySetting(
                    category='HARM_CATEGORY_DANGEROUS_CONTENT',
                    threshold='BLOCK_MEDIUM_AND_ABOVE'
                ),
            ]
        else:
            self.safety_settings = []
    
    def chat(self, model: str, messages: List[Dict[str, str]], options: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """Send a chat request to Google Gemini API using new SDK."""
        from google.genai import types
        
        # Build configuration with options and safety settings
        config_params = {
            'temperature': 0.1,
            'top_p': 0.8,
            'top_k': 40,
            'max_output_tokens': 8192,
        }
        
        # Override with user options, filtering out unsupported parameters
        if options:
            # List of supported GenerateContentConfig parameters
            supported_params = {
                'temperature', 'top_p', 'top_k', 'max_output_tokens', 
                'candidate_count', 'stop_sequences', 'response_mime_type'
            }
            
            # Filter options to only include supported parameters
            filtered_options = {k: v for k, v in options.items() if k in supported_params}
            config_params.update(filtered_options)
            
            # Log if any unsupported parameters were filtered out
            unsupported = set(options.keys()) - supported_params
            if unsupported:
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(f"Filtered out unsupported parameters: {unsupported}")
        
        # Handle different message patterns
        if len(messages) == 1:
            # Single message case
            contents = messages[0]['content']
            system_instruction = None
        else:
            # Multi-turn conversation
            contents = []
            system_instruction = None
            
            for msg in messages:
                if msg['role'] == 'system':
                    system_instruction = msg['content']
                elif msg['role'] == 'user':
                    contents.append({
                        'role': 'user',
                        'parts': [{'text': msg['content']}]
                    })
                elif msg['role'] == 'assistant':
                    contents.append({
                        'role': 'model',
                        'parts': [{'text': msg['content']}]
                    })
        
        # Create config object
        config = types.GenerateContentConfig(
            **{k: v for k, v in config_params.items()},
            safety_settings=self.safety_settings
        )
        
        if system_instruction:
            config.system_instruction = system_instruction
        
        try:
            # Use new generate_content method
            response = self.client.models.generate_content(
                model=model,
                contents=contents,
                config=config
            )
            
            # Enhanced response validation
            if not response.candidates:
                return {
                    'message': {
                        'role': 'assistant',
                        'content': 'No response generated. Please try again with different input.'
                    }
                }
            
            candidate = response.candidates[0]
            
            # Check finish reason
            if hasattr(candidate, 'finish_reason') and candidate.finish_reason:
                if candidate.finish_reason == 'SAFETY':
                    return {
                        'message': {
                            'role': 'assistant',
                            'content': 'Response was blocked due to safety filters. Please try rephrasing your request.'
                        }
                    }
                elif candidate.finish_reason == 'MAX_TOKENS':
                    # Still return the partial response
                    return {
                        'message': {
                            'role': 'assistant',
                            'content': f"{response.text}\n\n[Note: Response was truncated due to length limits]"
                        }
                    }
            
            # Return successful response
            return {
                'message': {
                    'role': 'assistant',
                    'content': response.text
                }
            }
            
        except Exception as e:
            # Comprehensive error handling
            error_message = self._handle_api_error(e)
            return {
                'message': {
                    'role': 'assistant',
                    'content': error_message
                }
            }
    
    def _handle_api_error(self, error: Exception) -> str:
        """Handle and categorize API errors."""
        error_str = str(error).lower()
        
        if "quota" in error_str or "limit" in error_str:
            return "API quota exceeded. Please check your Gemini API usage limits or try again later."
        elif "invalid" in error_str or "bad request" in error_str:
            return "Invalid request format. Please check your input and try again."
        elif "permission" in error_str or "unauthorized" in error_str or "403" in error_str:
            return "API authentication failed. Please check your GEMINI_API_KEY environment variable."
        elif "safety" in error_str:
            return "Content was blocked by safety filters. Please try rephrasing your request."
        elif "model" in error_str and "not found" in error_str:
            return "The specified model is not available. Please check the model name."
        elif "timeout" in error_str:
            return "Request timed out. Please try again."
        else:
            return f"Gemini API Error: {str(error)}"
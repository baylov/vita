"""AI-powered request analysis and response generation using Gemini."""

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from core.i18n import get_text
from exceptions import GeminiError
from services.gemini.client import GeminiClient

logger = logging.getLogger(__name__)


class RequestType(str, Enum):
    """Classification types for user requests."""

    APPOINTMENT_BOOKING = "appointment_booking"
    APPOINTMENT_CANCELLATION = "appointment_cancellation"
    APPOINTMENT_RESCHEDULING = "appointment_rescheduling"
    SCHEDULE_INQUIRY = "schedule_inquiry"
    SPECIALIST_INQUIRY = "specialist_inquiry"
    COMPLAINT = "complaint"
    FEEDBACK = "feedback"
    GENERAL_INQUIRY = "general_inquiry"
    OTHER = "other"


class UrgencyLevel(str, Enum):
    """Urgency levels for requests."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ClassificationResult:
    """Structured result of request classification."""

    def __init__(
        self,
        request_type: RequestType,
        urgency: UrgencyLevel,
        specialist_suggestion: Optional[str] = None,
        confidence: float = 0.5,
        reasoning: Optional[str] = None,
    ):
        self.request_type = request_type
        self.urgency = urgency
        self.specialist_suggestion = specialist_suggestion
        self.confidence = confidence
        self.reasoning = reasoning

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "request_type": self.request_type.value,
            "urgency": self.urgency.value,
            "specialist_suggestion": self.specialist_suggestion,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
        }


class ResponseResult:
    """Structured result of response generation."""

    def __init__(self, text: str, is_fallback: bool = False, error: Optional[str] = None):
        self.text = text
        self.is_fallback = is_fallback
        self.error = error


class CachedClassification:
    """Container for cached classification with TTL."""

    def __init__(self, result: ClassificationResult, ttl_seconds: int = 3600):
        self.result = result
        self.created_at = datetime.now(timezone.utc)
        self.ttl_seconds = ttl_seconds

    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        age = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        return age > self.ttl_seconds


class GeminiAnalyzer:
    """AI-powered request analyzer and response generator using Gemini."""

    def __init__(
        self,
        client: Optional[GeminiClient] = None,
        cache_ttl: int = 3600,
        notifier_callback: Optional[Callable[[str, str], None]] = None,
    ):
        """
        Initialize the Gemini analyzer.

        Args:
            client: GeminiClient instance (creates new one if not provided)
            cache_ttl: Cache TTL in seconds (default 3600)
            notifier_callback: Function to call on hard failures (service_name, error_msg)
        """
        try:
            self.client = client or GeminiClient()
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            raise GeminiError(f"Analyzer initialization failed: {e}")

        self.cache_ttl = cache_ttl
        self.notifier_callback = notifier_callback
        self._classification_cache: dict[str, CachedClassification] = {}

    def _get_cache_key(self, message: str, language: str) -> str:
        """Generate cache key from message hash and language."""
        message_hash = hashlib.md5(message.encode()).hexdigest()
        return f"{message_hash}:{language}"

    def _get_from_cache(self, key: str) -> Optional[ClassificationResult]:
        """Retrieve from cache if exists and not expired."""
        if key in self._classification_cache:
            cached = self._classification_cache[key]
            if not cached.is_expired():
                logger.debug(f"Cache hit for key: {key}")
                return cached.result
            else:
                logger.debug(f"Cache expired for key: {key}")
                del self._classification_cache[key]
        return None

    def _set_cache(self, key: str, result: ClassificationResult) -> None:
        """Store in cache."""
        self._classification_cache[key] = CachedClassification(result, self.cache_ttl)
        logger.debug(f"Cached classification for key: {key}")

    def clear_cache(self) -> None:
        """Clear all cached classifications."""
        self._classification_cache.clear()
        logger.info("Classification cache cleared")

    def _trigger_notifier(self, error_msg: str) -> None:
        """Trigger notifier callback on hard failures."""
        if self.notifier_callback:
            try:
                self.notifier_callback("gemini", error_msg)
                logger.info("Notifier callback triggered")
            except Exception as e:
                logger.error(f"Error in notifier callback: {e}")

    def classify_request(self, user_message: str, language: str = "ru") -> ClassificationResult:
        """
        Classify user message to determine request type and urgency.

        Args:
            user_message: User input text
            language: Language code ('ru' or 'kz')

        Returns:
            ClassificationResult with structured information

        Raises:
            GeminiError: If classification fails (after fallback attempt)
        """
        cache_key = self._get_cache_key(user_message, language)
        
        # Try to get from cache
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result

        # Prepare system instructions
        system_prompt = self._get_classification_prompt(language)

        try:
            model = self.client.get_model(language)
            generation_config = self.client.get_generation_config(
                temperature=0.3, max_output_tokens=300
            )
            
            response = genai.GenerativeModel(
                model,
                system_instruction=system_prompt,
                generation_config=generation_config,
                safety_settings=self.client.get_safety_settings(),
            ).generate_content(
                user_message,
                request_options={"timeout": self.client.get_request_timeout()},
            )

            result = self._parse_classification_response(response.text, language)
            self._set_cache(cache_key, result)
            return result

        except Exception as e:
            logger.error(f"Failed to classify request: {e}")
            self._trigger_notifier(f"Classification error: {str(e)}")
            
            # Return fallback classification
            fallback_result = ClassificationResult(
                request_type=RequestType.GENERAL_INQUIRY,
                urgency=UrgencyLevel.MEDIUM,
                confidence=0.0,
                reasoning="Fallback due to API error",
            )
            self._set_cache(cache_key, fallback_result)
            return fallback_result

    def generate_response(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None,
        language: str = "ru",
    ) -> ResponseResult:
        """
        Generate AI response to user message.

        Args:
            message: User message to respond to
            context: Additional context (specialist info, bookings, etc.)
            language: Language code ('ru' or 'kz')

        Returns:
            ResponseResult with generated text and fallback flag
        """
        system_prompt = self._get_response_prompt(language, context)

        try:
            model = self.client.get_model(language)
            generation_config = self.client.get_generation_config(
                temperature=0.7, max_output_tokens=500
            )
            
            response = genai.GenerativeModel(
                model,
                system_instruction=system_prompt,
                generation_config=generation_config,
                safety_settings=self.client.get_safety_settings(),
            ).generate_content(
                message,
                request_options={"timeout": self.client.get_request_timeout()},
            )

            return ResponseResult(text=response.text.strip(), is_fallback=False)

        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            self._trigger_notifier(f"Response generation error: {str(e)}")
            
            # Return fallback response from locales
            fallback_text = get_text("gemini.fallback_response", language)
            return ResponseResult(
                text=fallback_text,
                is_fallback=True,
                error=str(e),
            )

    def summarize_complaint(self, long_text: str, language: str = "ru") -> ResponseResult:
        """
        Summarize a long complaint or feedback text.

        Args:
            long_text: Long text to summarize
            language: Language code ('ru' or 'kz')

        Returns:
            ResponseResult with summarized text and fallback flag
        """
        system_prompt = self._get_summary_prompt(language)

        try:
            model = self.client.get_model(language)
            generation_config = self.client.get_generation_config(
                temperature=0.5, max_output_tokens=300
            )
            
            response = genai.GenerativeModel(
                model,
                system_instruction=system_prompt,
                generation_config=generation_config,
                safety_settings=self.client.get_safety_settings(),
            ).generate_content(
                long_text,
                request_options={"timeout": self.client.get_request_timeout()},
            )

            return ResponseResult(text=response.text.strip(), is_fallback=False)

        except Exception as e:
            logger.error(f"Failed to summarize complaint: {e}")
            self._trigger_notifier(f"Summary error: {str(e)}")
            
            # Return fallback summary from locales
            fallback_text = get_text("gemini.fallback_summary", language)
            return ResponseResult(
                text=fallback_text,
                is_fallback=True,
                error=str(e),
            )

    def _get_classification_prompt(self, language: str) -> str:
        """Get system prompt for classification task."""
        if language == "kz":
            return """Сіз құндыраш клиника администраторының көмекшісіз. 
Пайдаланушының хабарламасын талдап, келесі ақпаратты беріңіз JSON форматында:

{
  "request_type": одна из: appointment_booking, appointment_cancellation, appointment_rescheduling, schedule_inquiry, specialist_inquiry, complaint, feedback, general_inquiry, other
  "urgency": одна из: low, medium, high
  "specialist_suggestion": ұсынылған мамандық немесе null
  "confidence": 0-ден 1-ге дейінгі сан
  "reasoning": қысқа түсініктеме
}"""
        else:  # Russian default
            return """Вы помощник администратора клиники.
Проанализируйте сообщение пользователя и дайте ответ в формате JSON:

{
  "request_type": одна из: appointment_booking, appointment_cancellation, appointment_rescheduling, schedule_inquiry, specialist_inquiry, complaint, feedback, general_inquiry, other
  "urgency": одна из: low, medium, high
  "specialist_suggestion": рекомендуемая специальность или null
  "confidence": число от 0 до 1
  "reasoning": краткое обоснование
}"""

    def _get_response_prompt(self, language: str, context: Optional[dict] = None) -> str:
        """Get system prompt for response generation task."""
        context_str = ""
        if context:
            context_str = f"\n\nКонтекст: {json.dumps(context, ensure_ascii=False, indent=2)}"

        if language == "kz":
            return f"""Сіз құндыраш клиника администраторы болып әрекет етіңіз.
Құрметті, ресми, бірақ құлықты төлік беріңіз.
Клиникадан шымтаңыз және сөзді сәтті тілектеуді білдіңіз.{context_str}"""
        else:  # Russian default
            return f"""Вы администратор клиники.
Отвечайте вежливо, официально, но дружелюбно.
Помогайте клиентам с их запросами.{context_str}"""

    def _get_summary_prompt(self, language: str) -> str:
        """Get system prompt for summarization task."""
        if language == "kz":
            return """Берілген мәтінді қысқалау. Бірінші бір екі сөйлемде негіздеме жеткіліктіліктің негіздемесін:
- Негіздеме:
- Іс жүргіздеген ережелер:
- Өтінеме:"""
        else:  # Russian default
            return """Сделайте краткое резюме текста в 1-2 предложения. Укажите:
- Основная суть:
- Проблемная область:
- Требуемое действие:"""

    def _parse_classification_response(
        self, response_text: str, language: str
    ) -> ClassificationResult:
        """Parse classification response from Gemini."""
        try:
            # Extract JSON from response
            json_match = re.search(r"\{[\s\S]*\}", response_text)
            if not json_match:
                logger.warning(f"No JSON found in response: {response_text}")
                return ClassificationResult(
                    request_type=RequestType.GENERAL_INQUIRY,
                    urgency=UrgencyLevel.MEDIUM,
                )

            data = json.loads(json_match.group())

            request_type = RequestType(data.get("request_type", "other"))
            urgency = UrgencyLevel(data.get("urgency", "medium"))
            specialist_suggestion = data.get("specialist_suggestion")
            confidence = float(data.get("confidence", 0.5))
            reasoning = data.get("reasoning")

            return ClassificationResult(
                request_type=request_type,
                urgency=urgency,
                specialist_suggestion=specialist_suggestion,
                confidence=confidence,
                reasoning=reasoning,
            )

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse classification response: {e}")
            return ClassificationResult(
                request_type=RequestType.GENERAL_INQUIRY,
                urgency=UrgencyLevel.MEDIUM,
                reasoning="Parsing error",
            )

import json
import os
from typing import Optional, Dict, Any
from loguru import logger

# Безопасный импорт OpenAI
try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
    logger.info("OpenAI library imported successfully")
except ImportError as e:
    logger.error(f"OpenAI library not available: {e}")
    OPENAI_AVAILABLE = False

from models import Lead, Message, GPTAnalysis
from config import config


class GPTClient:
    """Клиент для работы с OpenAI GPT API"""

    def __init__(self):
        self.client = None
        self.model = "gpt-3.5-turbo"

        if not OPENAI_AVAILABLE:
            logger.error("OpenAI library not available")
            return

        try:
            # Проверяем API ключ
            api_key = config.openai_api_key
            if not api_key or api_key == "" or len(api_key) < 10:
                logger.error("Invalid or missing OpenAI API key")
                return

            logger.info("Initializing OpenAI client...")

            # Создаём клиент с минимальными параметрами
            self.client = OpenAI(api_key=api_key)

            logger.info("OpenAI client initialized successfully")

            # Тестируем подключение
            self._test_connection()

        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            self.client = None

    def _test_connection(self) -> bool:
        """Тестируем подключение к OpenAI"""
        if not self.client:
            return False

        try:
            logger.info("Testing OpenAI connection...")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": "Reply with just 'OK' if you can read this."}
                ],
                max_tokens=5,
                temperature=0
            )

            result = response.choices[0].message.content.strip()
            logger.info(f"Connection test successful: {result}")
            return True

        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def is_available(self) -> bool:
        """Проверяем доступность GPT клиента"""
        return self.client is not None

    def analyze_lead(self, lead: Lead) -> GPTAnalysis:
        """Анализ лида с помощью GPT"""
        if not self.is_available():
            logger.warning("GPT client not available, using fallback analysis")
            return self._get_fallback_analysis(lead)

        try:
            logger.info(f"Analyzing lead {lead.id} with GPT")

            prompt = self._build_lead_analysis_prompt(lead)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are an expert business assistant for {config.business_name}, 
                        specializing in {config.service_type}. Analyze customer leads and respond 
                        with valid JSON only."""
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800
            )

            result = response.choices[0].message.content.strip()
            logger.debug(f"GPT response: {result[:200]}...")

            # Парсим JSON ответ
            try:
                analysis_data = json.loads(result)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse GPT JSON response: {e}")
                return self._get_fallback_analysis(lead)

            # Создаём объект анализа
            analysis = GPTAnalysis(
                sentiment=analysis_data.get("sentiment", "neutral"),
                intent=analysis_data.get("intent", "quote_request"),
                urgency=analysis_data.get("urgency", "medium"),
                suggested_price=analysis_data.get("suggested_price"),
                key_requirements=analysis_data.get("key_requirements", []),
                suggested_response=analysis_data.get("suggested_response", ""),
                confidence_score=float(analysis_data.get("confidence_score", 0.8))
            )

            logger.info(f"Lead analysis completed: {analysis.intent}, ${analysis.suggested_price}")
            return analysis

        except Exception as e:
            logger.error(f"Error analyzing lead with GPT: {e}")
            return self._get_fallback_analysis(lead)

    def analyze_message(self, message: Message, lead: Optional[Lead] = None) -> GPTAnalysis:
        """Анализ сообщения от клиента"""
        if not self.is_available():
            return self._get_fallback_message_analysis(message)

        try:
            logger.info(f"Analyzing message {message.id} with GPT")

            prompt = self._build_message_analysis_prompt(message, lead)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are a business assistant for {config.business_name}. 
                        Analyze customer messages and respond with valid JSON only."""
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=600
            )

            result = response.choices[0].message.content.strip()

            try:
                analysis_data = json.loads(result)
            except json.JSONDecodeError:
                return self._get_fallback_message_analysis(message)

            analysis = GPTAnalysis(
                sentiment=analysis_data.get("sentiment", "neutral"),
                intent=analysis_data.get("intent", "question"),
                urgency=analysis_data.get("urgency", "medium"),
                suggested_price=analysis_data.get("suggested_price"),
                key_requirements=analysis_data.get("key_requirements", []),
                suggested_response=analysis_data.get("suggested_response", ""),
                confidence_score=float(analysis_data.get("confidence_score", 0.8))
            )

            logger.info(f"Message analysis completed: {analysis.intent}")
            return analysis

        except Exception as e:
            logger.error(f"Error analyzing message with GPT: {e}")
            return self._get_fallback_message_analysis(message)

    def generate_quote_response(self, lead: Lead, price: float, additional_info: str = "") -> str:
        """Генерация ответа с ценовым предложением"""
        if not self.is_available():
            return self._get_fallback_quote_response(lead, price, additional_info)

        try:
            logger.info(f"Generating quote response for lead {lead.id}")

            prompt = f"""
Generate a professional quote response for a {config.service_type.lower()} business.

Customer: {lead.customer_name}
Service: {lead.description}
Quoted Price: ${price:.2f}
Additional Info: {additional_info}
Business: {config.business_name}

Write a friendly, professional response that:
- Thanks the customer
- Clearly states the price
- Addresses their specific needs
- Includes next steps
- Sounds natural and personal

Response (no JSON, just the message text):
            """

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a professional {config.service_type.lower()} business owner."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=400
            )

            quote_response = response.choices[0].message.content.strip()
            logger.info(f"Quote response generated ({len(quote_response)} chars)")
            return quote_response

        except Exception as e:
            logger.error(f"Error generating quote response: {e}")
            return self._get_fallback_quote_response(lead, price, additional_info)

    def _get_fallback_analysis(self, lead: Lead) -> GPTAnalysis:
        """Базовый анализ когда GPT недоступен"""
        suggested_price = config.base_price

        # Простая логика ценообразования
        if lead.budget_range:
            min_budget, max_budget = lead.budget_range
            suggested_price = min(max_budget, max(min_budget, config.base_price))

        return GPTAnalysis(
            sentiment="neutral",
            intent="quote_request",
            urgency="medium",
            suggested_price=suggested_price,
            key_requirements=[lead.service_category],
            suggested_response=f"Thank you for your interest in our {config.service_type.lower()} services. We'd be happy to help with {lead.description[:50]}...",
            confidence_score=0.5
        )

    def _get_fallback_message_analysis(self, message: Message) -> GPTAnalysis:
        """Базовый анализ сообщения"""
        return GPTAnalysis(
            sentiment="neutral",
            intent="question",
            urgency="medium",
            suggested_response="Thank you for your message. We'll get back to you shortly.",
            confidence_score=0.5
        )

    def _get_fallback_quote_response(self, lead: Lead, price: float, additional_info: str = "") -> str:
        """Базовый ответ с расценками"""
        return f"""
Hi {lead.customer_name},

Thank you for your interest in {config.business_name}!

Based on your request for {lead.description}, I'm pleased to offer you a quote of ${price:.2f}.

{additional_info}

Please let me know if you have any questions or would like to schedule the work.

Best regards,
{config.business_name}
        """.strip()

    def _build_lead_analysis_prompt(self, lead: Lead) -> str:
        """Построение промпта для анализа лида"""
        return f"""
Analyze this customer lead and respond with valid JSON only:

{{
    "sentiment": "positive|neutral|negative",
    "intent": "quote_request|scheduling|question|other", 
    "urgency": "high|medium|low",
    "suggested_price": number_or_null,
    "key_requirements": ["req1", "req2"],
    "suggested_response": "response text",
    "confidence_score": 0.8
}}

Customer: {lead.customer_name}
Service: {lead.service_category}
Description: {lead.description}
Budget: {lead.budget_range if lead.budget_range else 'Not specified'}
Date: {lead.preferred_date if lead.preferred_date else 'Not specified'}
Location: {lead.location if lead.location else 'Not specified'}

Business: {config.business_name} ({config.service_type})
Price range: ${config.price_range_min}-${config.price_range_max}
        """

    def _build_message_analysis_prompt(self, message: Message, lead: Optional[Lead] = None) -> str:
        """Построение промпта для анализа сообщения"""
        lead_context = ""
        if lead:
            lead_context = f"\nLead context: {lead.customer_name} - {lead.description}"

        return f"""
Analyze this message and respond with valid JSON only:

{{
    "sentiment": "positive|neutral|negative",
    "intent": "scheduling|question|booking|complaint|other",
    "urgency": "high|medium|low", 
    "suggested_response": "response text",
    "confidence_score": 0.8
}}

Message: {message.content}
Sender: {message.sender}{lead_context}

Business: {config.business_name}
        """
import json
from typing import Optional, Dict, Any
from openai import OpenAI
from loguru import logger

from models import Lead, Message, GPTAnalysis
from config import config


class GPTClient:
    """Клиент для работы с OpenAI GPT API"""
    
    def __init__(self):
        self.client = OpenAI(api_key=config.openai_api_key)
        self.model = "gpt-4"  # или "gpt-3.5-turbo" для более быстрой работы
    
    def analyze_lead(self, lead: Lead) -> GPTAnalysis:
        """Анализ лида с помощью GPT"""
        try:
            logger.info(f"Analyzing lead {lead.id}")
            
            prompt = self._build_lead_analysis_prompt(lead)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are an expert business assistant for {config.business_name}, 
                        specializing in {config.service_type}. Your job is to analyze customer leads 
                        and provide structured responses in JSON format."""
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            result = response.choices[0].message.content
            analysis_data = json.loads(result)
            
            analysis = GPTAnalysis(
                sentiment=analysis_data.get("sentiment", "neutral"),
                intent=analysis_data.get("intent", "quote_request"),
                urgency=analysis_data.get("urgency", "medium"),
                suggested_price=analysis_data.get("suggested_price"),
                key_requirements=analysis_data.get("key_requirements", []),
                suggested_response=analysis_data.get("suggested_response", ""),
                confidence_score=analysis_data.get("confidence_score", 0.8)
            )
            
            logger.info(f"Lead analysis completed for {lead.id}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing lead: {e}")
            # Возвращаем базовый анализ в случае ошибки
            return GPTAnalysis(
                sentiment="neutral",
                intent="quote_request",
                urgency="medium",
                suggested_price=config.base_price,
                key_requirements=[],
                suggested_response=f"Thank you for your interest in our {config.service_type.lower()} services. We'd be happy to provide you with a quote.",
                confidence_score=0.5
            )
    
    def analyze_message(self, message: Message, lead: Optional[Lead] = None) -> GPTAnalysis:
        """Анализ сообщения от клиента"""
        try:
            logger.info(f"Analyzing message {message.id}")
            
            prompt = self._build_message_analysis_prompt(message, lead)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are an expert business assistant for {config.business_name}, 
                        specializing in {config.service_type}. Analyze customer messages and provide 
                        structured responses in JSON format."""
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            result = response.choices[0].message.content
            analysis_data = json.loads(result)
            
            analysis = GPTAnalysis(
                sentiment=analysis_data.get("sentiment", "neutral"),
                intent=analysis_data.get("intent", "question"),
                urgency=analysis_data.get("urgency", "medium"),
                suggested_price=analysis_data.get("suggested_price"),
                key_requirements=analysis_data.get("key_requirements", []),
                suggested_response=analysis_data.get("suggested_response", ""),
                confidence_score=analysis_data.get("confidence_score", 0.8)
            )
            
            logger.info(f"Message analysis completed for {message.id}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing message: {e}")
            return GPTAnalysis(
                sentiment="neutral",
                intent="question",
                urgency="medium",
                suggested_response="Thank you for your message. We'll get back to you shortly.",
                confidence_score=0.5
            )
    
    def generate_quote_response(self, lead: Lead, price: float, additional_info: str = "") -> str:
        """Генерация ответа с ценовым предложением"""
        try:
            logger.info(f"Generating quote response for lead {lead.id}")
            
            prompt = f"""
            Generate a professional quote response for a {config.service_type.lower()} business.
            
            Customer: {lead.customer_name}
            Service requested: {lead.description}
            Suggested price: ${price:.2f}
            Additional information: {additional_info}
            Business name: {config.business_name}
            
            The response should be:
            - Professional and friendly
            - Include the price clearly
            - Address specific customer requirements
            - Include next steps
            - Be concise but complete
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a professional {config.service_type.lower()} business owner writing quotes to potential customers."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800
            )
            
            quote_response = response.choices[0].message.content
            logger.info(f"Quote response generated for lead {lead.id}")
            return quote_response
            
        except Exception as e:
            logger.error(f"Error generating quote response: {e}")
            return f"""
Thank you for your interest in our {config.service_type.lower()} services!

Based on your requirements, I'm pleased to offer you a quote of ${price:.2f}.

Please let me know if you have any questions or would like to discuss the details further.

Best regards,
{config.business_name}
            """.strip()
    
    def _build_lead_analysis_prompt(self, lead: Lead) -> str:
        """Построение промпта для анализа лида"""
        return f"""
        Analyze this customer lead and provide a JSON response with the following structure:
        {{
            "sentiment": "positive|neutral|negative",
            "intent": "quote_request|scheduling|question|complaint|other",
            "urgency": "high|medium|low",
            "suggested_price": float_or_null,
            "key_requirements": ["requirement1", "requirement2"],
            "suggested_response": "Professional response text",
            "confidence_score": float_between_0_and_1
        }}
        
        Customer Information:
        - Name: {lead.customer_name}
        - Service Category: {lead.service_category}
        - Description: {lead.description}
        - Budget Range: {lead.budget_range if lead.budget_range else 'Not specified'}
        - Preferred Date: {lead.preferred_date if lead.preferred_date else 'Not specified'}
        - Location: {lead.location if lead.location else 'Not specified'}
        
        Business Context:
        - Service Type: {config.service_type}
        - Base Price: ${config.base_price}
        - Price Range: ${config.price_range_min} - ${config.price_range_max}
        
        Provide pricing suggestions within our range and craft a professional response.
        """
    
    def _build_message_analysis_prompt(self, message: Message, lead: Optional[Lead] = None) -> str:
        """Построение промпта для анализа сообщения"""
        lead_context = ""
        if lead:
            lead_context = f"""
            Lead Context:
            - Customer: {lead.customer_name}
            - Service: {lead.service_category}
            - Original Request: {lead.description}
            - Status: {lead.status}
            """
        
        return f"""
        Analyze this customer message and provide a JSON response with the following structure:
        {{
            "sentiment": "positive|neutral|negative",
            "intent": "quote_request|scheduling|question|complaint|booking|other",
            "urgency": "high|medium|low",
            "suggested_price": float_or_null,
            "key_requirements": ["requirement1", "requirement2"],
            "suggested_response": "Professional response text",
            "confidence_score": float_between_0_and_1
        }}
        
        Message Details:
        - Sender: {message.sender}
        - Content: {message.content}
        - Type: {message.message_type}
        
        {lead_context}
        
        Business Context:
        - Service Type: {config.service_type}
        - Business Name: {config.business_name}
        
        Craft an appropriate professional response based on the message intent.
        """
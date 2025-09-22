import time
import schedule
from datetime import datetime, timedelta
from typing import List, Dict
from loguru import logger
import sys

from config import config
from models import Lead, Message, CalendarEvent, LeadStatus
from thumbtack_client import ThumbtackClient
from gpt_client import GPTClient
from calendar_client import CalendarClient


class ThumbtackBot:
    """Основной класс бота для автоматизации работы с Thumbtack"""
    
    def __init__(self):
        self.thumbtack_client = ThumbtackClient()
        self.gpt_client = GPTClient()
        self.calendar_client = CalendarClient()
        self.processed_leads: Dict[str, datetime] = {}
        self.processed_messages: Dict[str, datetime] = {}
        
        # Настройка логирования
        logger.remove()
        logger.add(
            sys.stdout,
            level=config.log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        )
        logger.add(
            "logs/thumbtack_bot.log",
            level=config.log_level,
            rotation="1 day",
            retention="30 days",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
        )
    
    def initialize(self) -> bool:
        """Инициализация всех клиентов"""
        logger.info("Initializing Thumbtack Bot...")
        
        # Инициализация Thumbtack клиента
        if not self.thumbtack_client.authenticate():
            logger.error("Failed to authenticate with Thumbtack")
            return False
        
        # Инициализация Calendar клиента
        if not self.calendar_client.authenticate():
            logger.error("Failed to authenticate with Google Calendar")
            return False
        
        logger.info("All clients initialized successfully")
        return True
    
    def process_new_leads(self):
        """Обработка новых лидов"""
        try:
            logger.info("Processing new leads...")
            
            new_leads = self.thumbtack_client.get_new_leads()
            
            for lead in new_leads:
                if lead.id in self.processed_leads:
                    continue
                
                logger.info(f"Processing new lead: {lead.id} from {lead.customer_name}")
                
                # Анализируем лид с помощью GPT
                analysis = self.gpt_client.analyze_lead(lead)
                
                # Обрабатываем в зависимости от намерения
                if analysis.intent == "quote_request":
                    self._handle_quote_request(lead, analysis)
                elif analysis.intent == "scheduling":
                    self._handle_scheduling_request(lead, analysis)
                else:
                    self._handle_general_inquiry(lead, analysis)
                
                # Отмечаем как обработанный
                self.processed_leads[lead.id] = datetime.now()
                
                # Обновляем статус лида
                self.thumbtack_client.update_lead_status(lead.id, LeadStatus.CONTACTED)
            
            if new_leads:
                logger.info(f"Processed {len(new_leads)} new leads")
            
        except Exception as e:
            logger.error(f"Error processing new leads: {e}")
    
    def process_new_messages(self):
        """Обработка новых сообщений"""
        try:
            logger.info("Processing new messages...")
            
            new_messages = self.thumbtack_client.get_new_messages()
            
            for message in new_messages:
                if message.id in self.processed_messages or message.sender == "business":
                    continue
                
                logger.info(f"Processing new message: {message.id} from lead {message.lead_id}")
                
                # Получаем информацию о лиде если возможно
                lead = self._get_lead_by_id(message.lead_id)
                
                # Анализируем сообщение с помощью GPT
                analysis = self.gpt_client.analyze_message(message, lead)
                
                # Обрабатываем в зависимости от намерения
                if analysis.intent == "scheduling":
                    self._handle_scheduling_message(message, lead, analysis)
                elif analysis.intent == "booking":
                    self._handle_booking_confirmation(message, lead, analysis)
                elif analysis.intent == "question":
                    self._handle_question(message, lead, analysis)
                else:
                    self._handle_general_message(message, lead, analysis)
                
                # Отмечаем как обработанный
                self.processed_messages[message.id] = datetime.now()
            
            if new_messages:
                logger.info(f"Processed {len(new_messages)} new messages")
            
        except Exception as e:
            logger.error(f"Error processing new messages: {e}")
    
    def _handle_quote_request(self, lead: Lead, analysis):
        """Обработка запроса на расценки"""
        try:
            logger.info(f"Handling quote request for lead {lead.id}")
            
            # Определяем цену на основе анализа GPT
            suggested_price = analysis.suggested_price or config.base_price
            
            # Учитываем бюджет клиента если указан
            if lead.budget_range:
                min_budget, max_budget = lead.budget_range
                if suggested_price > max_budget:
                    suggested_price = max_budget
                elif suggested_price < min_budget:
                    suggested_price = min_budget
            
            # Генерируем персонализированный ответ
            quote_response = self.gpt_client.generate_quote_response(
                lead, suggested_price, 
                f"Key requirements: {', '.join(analysis.key_requirements)}"
            )
            
            # Отправляем расценки
            success = self.thumbtack_client.send_quote(lead.id, suggested_price, quote_response)
            
            if success:
                logger.info(f"Quote sent successfully to {lead.customer_name}: ${suggested_price:.2f}")
            else:
                logger.error(f"Failed to send quote to lead {lead.id}")
            
        except Exception as e:
            logger.error(f"Error handling quote request: {e}")
    
    def _handle_scheduling_request(self, lead: Lead, analysis):
        """Обработка запроса на планирование"""
        try:
            logger.info(f"Handling scheduling request for lead {lead.id}")
            
            # Получаем предпочтительную дату из лида
            preferred_date = lead.preferred_date or (datetime.now() + timedelta(days=7))
            
            # Предлагаем доступное время
            available_times = self.calendar_client.suggest_meeting_times(preferred_date)
            
            if available_times:
                time_options = "\n".join([
                    f"• {time.strftime('%A, %B %d at %I:%M %p')}" 
                    for time in available_times[:3]
                ])
                
                response = f"""
Thank you for your interest in scheduling our {config.service_type.lower()} services!

Based on your preferences, I have the following time slots available:

{time_options}

Please let me know which time works best for you, and I'll confirm the appointment.

Best regards,
{config.business_name}
                """.strip()
            else:
                response = f"""
Thank you for your scheduling request. I'm currently checking my availability and will get back to you within a few hours with available time slots.

Best regards,
{config.business_name}
                """.strip()
            
            self.thumbtack_client.send_message(lead.id, response)
            
        except Exception as e:
            logger.error(f"Error handling scheduling request: {e}")
    
    def _handle_general_inquiry(self, lead: Lead, analysis):
        """Обработка общих запросов"""
        try:
            logger.info(f"Handling general inquiry for lead {lead.id}")
            
            # Используем ответ, сгенерированный GPT
            response = analysis.suggested_response
            
            if not response:
                response = f"""
Thank you for your interest in {config.business_name}!

I'd be happy to discuss your {config.service_type.lower()} needs. Please let me know:
- When you're looking to schedule the service
- Any specific requirements you have
- Your preferred budget range

I'll provide you with a detailed quote and available scheduling options.

Best regards,
{config.business_name}
                """.strip()
            
            self.thumbtack_client.send_message(lead.id, response)
            
        except Exception as e:
            logger.error(f"Error handling general inquiry: {e}")
    
    def _handle_scheduling_message(self, message: Message, lead, analysis):
        """Обработка сообщения о планировании"""
        try:
            logger.info(f"Handling scheduling message for lead {message.lead_id}")
            
            # Извлекаем информацию о времени из сообщения (упрощенная версия)
            # В реальной реализации здесь может быть более сложная логика парсинга
            
            available_times = self.calendar_client.suggest_meeting_times()
            
            if available_times:
                time_options = "\n".join([
                    f"• {time.strftime('%A, %B %d at %I:%M %p')}" 
                    for time in available_times[:3]
                ])
                
                response = f"""
I have the following available time slots:

{time_options}

Please confirm which time works best for you, and I'll send you a calendar invitation.
                """.strip()
            else:
                response = "I'm currently checking my schedule and will get back to you shortly with available times."
            
            self.thumbtack_client.send_message(message.lead_id, response)
            
        except Exception as e:
            logger.error(f"Error handling scheduling message: {e}")
    
    def _handle_booking_confirmation(self, message: Message, lead, analysis):
        """Обработка подтверждения бронирования"""
        try:
            logger.info(f"Handling booking confirmation for lead {message.lead_id}")
            
            # В реальной реализации здесь будет парсинг подтвержденного времени
            # Для демонстрации создаем событие на завтра
            start_time = datetime.now().replace(hour=14, minute=0, second=0, microsecond=0) + timedelta(days=1)
            end_time = start_time + timedelta(hours=2)
            
            # Создаем событие в календаре
            calendar_event = CalendarEvent(
                lead_id=message.lead_id,
                title=f"{config.service_type} - {lead.customer_name if lead else 'Client'}",
                description=f"Lead ID: {message.lead_id}\nService: {config.service_type}\n\nGenerated by Thumbtack Bot",
                start_time=start_time,
                end_time=end_time,
                attendees=[lead.customer_email] if lead and lead.customer_email else []
            )
            
            event_id = self.calendar_client.create_event(calendar_event)
            
            if event_id:
                response = f"""
Great! Your {config.service_type.lower()} appointment has been confirmed for {start_time.strftime('%A, %B %d at %I:%M %p')}.

You'll receive a calendar invitation shortly. If you need to reschedule or have any questions, please don't hesitate to reach out.

Looking forward to working with you!

Best regards,
{config.business_name}
                """.strip()
                
                # Обновляем статус лида
                self.thumbtack_client.update_lead_status(message.lead_id, LeadStatus.BOOKED)
            else:
                response = "I'm confirming your appointment and will send you the details shortly."
            
            self.thumbtack_client.send_message(message.lead_id, response)
            
        except Exception as e:
            logger.error(f"Error handling booking confirmation: {e}")
    
    def _handle_question(self, message: Message, lead, analysis):
        """Обработка вопросов"""
        response = analysis.suggested_response or "Thank you for your question. I'll get back to you shortly with a detailed answer."
        self.thumbtack_client.send_message(message.lead_id, response)
    
    def _handle_general_message(self, message: Message, lead, analysis):
        """Обработка общих сообщений"""
        response = analysis.suggested_response or "Thank you for your message. I'll review it and get back to you soon."
        self.thumbtack_client.send_message(message.lead_id, response)
    
    def _get_lead_by_id(self, lead_id: str):
        """Получение лида по ID (упрощенная версия)"""
        # В реальной реализации здесь будет запрос к базе данных или API
        return None
    
    def run_once(self):
        """Однократное выполнение обработки"""
        logger.info("Running Thumbtack Bot cycle...")
        self.process_new_leads()
        self.process_new_messages()
        logger.info("Cycle completed")
    
    def run_daemon(self):
        """Запуск в режиме демона"""
        logger.info(f"Starting Thumbtack Bot daemon (checking every {config.check_interval_minutes} minutes)")
        
        # Планируем выполнение каждые N минут
        schedule.every(config.check_interval_minutes).minutes.do(self.run_once)
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Проверяем каждую минуту
        except KeyboardInterrupt:
            logger.info("Shutting down Thumbtack Bot...")
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Корректное завершение работы"""
        logger.info("Shutting down...")
        if self.thumbtack_client:
            self.thumbtack_client.disconnect()


def main():
    """Основная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Thumbtack Automation Bot')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon')
    args = parser.parse_args()
    
    bot = ThumbtackBot()
    
    if not bot.initialize():
        logger.error("Failed to initialize bot")
        sys.exit(1)
    
    try:
        if args.once:
            bot.run_once()
        elif args.daemon:
            bot.run_daemon()
        else:
            # По умолчанию запускаем как демон
            bot.run_daemon()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
import json
import time
import random
from datetime import datetime, timedelta
from typing import List, Optional
from loguru import logger

from models import Lead, Message, LeadStatus, MessageType
from config import config


class ThumbtackClient:
    """
    Клиент для работы с Thumbtack.
    В данной реализации имитирует работу с сервисом,
    но может быть заменен на реальную интеграцию.
    """
    
    def __init__(self):
        self.session_active = False
        self.leads_data_file = "mock_leads.json"
        self.messages_data_file = "mock_messages.json"
        self._init_mock_data()
    
    def _init_mock_data(self):
        """Инициализация тестовых данных"""
        try:
            with open(self.leads_data_file, 'r') as f:
                self.mock_leads = json.load(f)
        except FileNotFoundError:
            self.mock_leads = []
            self._generate_mock_leads()
            self._save_mock_data()
        
        try:
            with open(self.messages_data_file, 'r') as f:
                self.mock_messages = json.load(f)
        except FileNotFoundError:
            self.mock_messages = []
    
    def _generate_mock_leads(self):
        """Генерация тестовых лидов"""
        sample_leads = [
            {
                "id": f"lead_{int(time.time())}_{i}",
                "customer_name": f"John Doe {i}",
                "customer_email": f"john.doe{i}@example.com",
                "customer_phone": f"+1555000{i:04d}",
                "service_category": config.service_type,
                "description": f"Need {config.service_type.lower()} services for a special event. Please provide a quote.",
                "budget_range": [config.price_range_min, config.price_range_max],
                "preferred_date": (datetime.now() + timedelta(days=random.randint(1, 30))).isoformat(),
                "location": "New York, NY",
                "status": "new",
                "created_at": datetime.now().isoformat(),
                "metadata": {"source": "thumbtack_mock"}
            }
            for i in range(1, 4)
        ]
        self.mock_leads.extend(sample_leads)
    
    def _save_mock_data(self):
        """Сохранение данных в файлы"""
        with open(self.leads_data_file, 'w') as f:
            json.dump(self.mock_leads, f, indent=2, default=str)
        
        with open(self.messages_data_file, 'w') as f:
            json.dump(self.mock_messages, f, indent=2, default=str)
    
    def authenticate(self) -> bool:
        """
        Аутентификация в Thumbtack.
        В реальной реализации здесь будет логин или API аутентификация.
        """
        try:
            # Имитация процесса входа
            logger.info("Authenticating with Thumbtack...")
            time.sleep(1)  # Имитация задержки
            
            if config.thumbtack_email and config.thumbtack_password:
                logger.info(f"Using credentials for {config.thumbtack_email}")
                # Здесь будет реальная аутентификация
                self.session_active = True
                return True
            else:
                logger.warning("No Thumbtack credentials provided, using mock mode")
                self.session_active = True
                return True
                
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    def get_new_leads(self) -> List[Lead]:
        """
        Получение новых лидов.
        В реальной реализации будет делать запрос к Thumbtack API.
        """
        try:
            if not self.session_active:
                logger.warning("Not authenticated with Thumbtack")
                return []
            
            logger.info("Checking for new leads...")
            
            # Имитация получения новых лидов
            new_leads = []
            for lead_data in self.mock_leads:
                if lead_data["status"] == "new":
                    lead = Lead(
                        id=lead_data["id"],
                        customer_name=lead_data["customer_name"],
                        customer_email=lead_data.get("customer_email"),
                        customer_phone=lead_data.get("customer_phone"),
                        service_category=lead_data["service_category"],
                        description=lead_data["description"],
                        budget_range=tuple(lead_data["budget_range"]) if lead_data.get("budget_range") else None,
                        preferred_date=datetime.fromisoformat(lead_data["preferred_date"]) if lead_data.get("preferred_date") else None,
                        location=lead_data.get("location"),
                        status=LeadStatus(lead_data["status"]),
                        created_at=datetime.fromisoformat(lead_data["created_at"]),
                        metadata=lead_data.get("metadata", {})
                    )
                    new_leads.append(lead)
            
            logger.info(f"Found {len(new_leads)} new leads")
            return new_leads
            
        except Exception as e:
            logger.error(f"Error getting new leads: {e}")
            return []
    
    def get_new_messages(self, lead_id: Optional[str] = None) -> List[Message]:
        """
        Получение новых сообщений.
        В реальной реализации будет делать запрос к Thumbtack API.
        """
        try:
            if not self.session_active:
                logger.warning("Not authenticated with Thumbtack")
                return []
            
            logger.info(f"Checking for new messages{f' for lead {lead_id}' if lead_id else ''}")
            
            # Имитация получения новых сообщений
            new_messages = []
            for msg_data in self.mock_messages:
                if lead_id and msg_data["lead_id"] != lead_id:
                    continue
                
                message = Message(
                    id=msg_data["id"],
                    lead_id=msg_data["lead_id"],
                    sender=msg_data["sender"],
                    content=msg_data["content"],
                    message_type=MessageType(msg_data.get("message_type", "message")),
                    timestamp=datetime.fromisoformat(msg_data["timestamp"]),
                    metadata=msg_data.get("metadata", {})
                )
                new_messages.append(message)
            
            logger.info(f"Found {len(new_messages)} new messages")
            return new_messages
            
        except Exception as e:
            logger.error(f"Error getting new messages: {e}")
            return []
    
    def send_message(self, lead_id: str, content: str) -> bool:
        """
        Отправка сообщения клиенту.
        В реальной реализации будет отправлять через Thumbtack API.
        """
        try:
            logger.info(f"Sending message to lead {lead_id}")
            
            # Имитация отправки сообщения
            message_data = {
                "id": f"msg_{int(time.time())}_{random.randint(1000, 9999)}",
                "lead_id": lead_id,
                "sender": "business",
                "content": content,
                "message_type": "message",
                "timestamp": datetime.now().isoformat(),
                "metadata": {"sent_by": "bot"}
            }
            
            self.mock_messages.append(message_data)
            self._save_mock_data()
            
            logger.info(f"Message sent successfully to lead {lead_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    def update_lead_status(self, lead_id: str, status: LeadStatus) -> bool:
        """Обновление статуса лида"""
        try:
            for lead_data in self.mock_leads:
                if lead_data["id"] == lead_id:
                    lead_data["status"] = status.value
                    self._save_mock_data()
                    logger.info(f"Updated lead {lead_id} status to {status.value}")
                    return True
            
            logger.warning(f"Lead {lead_id} not found")
            return False
            
        except Exception as e:
            logger.error(f"Error updating lead status: {e}")
            return False
    
    def send_quote(self, lead_id: str, price: float, description: str) -> bool:
        """
        Отправка ценового предложения.
        В реальной реализации будет отправлять через Thumbtack API.
        """
        try:
            quote_message = f"""
Thank you for your interest in our {config.service_type.lower()} services!

Based on your requirements, I'm pleased to offer you the following quote:

Price: ${price:.2f}
Details: {description}

This quote is valid for the next 7 days. If you have any questions or would like to discuss the details further, please don't hesitate to reach out.

I look forward to working with you!

Best regards,
{config.business_name}
            """.strip()
            
            success = self.send_message(lead_id, quote_message)
            if success:
                self.update_lead_status(lead_id, LeadStatus.QUOTED)
                logger.info(f"Quote sent to lead {lead_id}: ${price:.2f}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending quote: {e}")
            return False
    
    def disconnect(self):
        """Завершение сессии"""
        logger.info("Disconnecting from Thumbtack")
        self.session_active = False
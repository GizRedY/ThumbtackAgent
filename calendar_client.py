import os
import pickle
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from loguru import logger

from models import CalendarEvent
from config import config


class CalendarClient:
    """Клиент для работы с Google Calendar API"""
    
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    
    def __init__(self):
        self.service = None
        self.calendar_id = config.google_calendar_id
        self.credentials = None
        
    def authenticate(self) -> bool:
        """Аутентификация в Google Calendar API"""
        try:
            logger.info("Authenticating with Google Calendar API...")
            
            # Загружаем токен если он существует
            if os.path.exists('token.pickle'):
                with open('token.pickle', 'rb') as token:
                    self.credentials = pickle.load(token)
            
            # Если нет валидных учетных данных
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                else:
                    if not os.path.exists(config.google_calendar_credentials_file):
                        logger.error(f"Credentials file not found: {config.google_calendar_credentials_file}")
                        logger.info("Please download credentials.json from Google Cloud Console")
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        config.google_calendar_credentials_file, self.SCOPES
                    )
                    self.credentials = flow.run_local_server(port=0)
                
                # Сохраняем учетные данные для следующего запуска
                with open('token.pickle', 'wb') as token:
                    pickle.dump(self.credentials, token)
            
            self.service = build('calendar', 'v3', credentials=self.credentials)
            logger.info("Successfully authenticated with Google Calendar API")
            return True
            
        except Exception as e:
            logger.error(f"Error authenticating with Google Calendar: {e}")
            return False
    
    def check_availability(self, start_time: datetime, end_time: datetime) -> bool:
        """Проверка доступности в указанное время"""
        try:
            if not self.service:
                logger.error("Calendar service not initialized")
                return False
            
            logger.info(f"Checking availability from {start_time} to {end_time}")
            
            # Получаем события в указанном временном диапазоне
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=start_time.isoformat() + 'Z',
                timeMax=end_time.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            if not events:
                logger.info("No conflicts found - time slot is available")
                return True
            
            # Проверяем пересечения с существующими событиями
            for event in events:
                event_start = event['start'].get('dateTime', event['start'].get('date'))
                event_end = event['end'].get('dateTime', event['end'].get('date'))
                
                if event_start and event_end:
                    event_start_dt = datetime.fromisoformat(event_start.replace('Z', '+00:00'))
                    event_end_dt = datetime.fromisoformat(event_end.replace('Z', '+00:00'))
                    
                    # Проверяем пересечение
                    if (start_time < event_end_dt and end_time > event_start_dt):
                        logger.info(f"Time conflict found with event: {event.get('summary', 'Unnamed event')}")
                        return False
            
            logger.info("No conflicts found - time slot is available")
            return True
            
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            return False
    
    def get_available_slots(self, date: datetime, duration_hours: float = 2.0, 
                           business_hours: Tuple[int, int] = (9, 17)) -> List[datetime]:
        """Получение доступных временных слотов на указанную дату"""
        try:
            if not self.service:
                logger.error("Calendar service not initialized")
                return []
            
            logger.info(f"Finding available slots for {date.date()}")
            
            available_slots = []
            start_hour, end_hour = business_hours
            
            # Проверяем каждый час в рабочее время
            current_time = date.replace(hour=start_hour, minute=0, second=0, microsecond=0)
            end_time = date.replace(hour=end_hour, minute=0, second=0, microsecond=0)
            
            while current_time + timedelta(hours=duration_hours) <= end_time:
                slot_end = current_time + timedelta(hours=duration_hours)
                
                if self.check_availability(current_time, slot_end):
                    available_slots.append(current_time)
                
                current_time += timedelta(hours=1)  # Проверяем каждый час
            
            logger.info(f"Found {len(available_slots)} available slots")
            return available_slots
            
        except Exception as e:
            logger.error(f"Error getting available slots: {e}")
            return []
    
    def create_event(self, event: CalendarEvent) -> Optional[str]:
        """Создание события в календаре"""
        try:
            if not self.service:
                logger.error("Calendar service not initialized")
                return None
            
            logger.info(f"Creating calendar event: {event.title}")
            
            event_body = {
                'summary': event.title,
                'description': event.description,
                'start': {
                    'dateTime': event.start_time.isoformat(),
                    'timeZone': config.timezone,
                },
                'end': {
                    'dateTime': event.end_time.isoformat(),
                    'timeZone': config.timezone,
                },
                'attendees': [{'email': email} for email in event.attendees] if event.attendees else [],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                        {'method': 'popup', 'minutes': 60},       # 1 hour before
                    ],
                },
            }
            
            if event.location:
                event_body['location'] = event.location
            
            created_event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event_body
            ).execute()
            
            event_id = created_event.get('id')
            logger.info(f"Event created successfully with ID: {event_id}")
            return event_id
            
        except Exception as e:
            logger.error(f"Error creating calendar event: {e}")
            return None
    
    def update_event(self, event_id: str, event: CalendarEvent) -> bool:
        """Обновление существующего события"""
        try:
            if not self.service:
                logger.error("Calendar service not initialized")
                return False
            
            logger.info(f"Updating calendar event: {event_id}")
            
            event_body = {
                'summary': event.title,
                'description': event.description,
                'start': {
                    'dateTime': event.start_time.isoformat(),
                    'timeZone': config.timezone,
                },
                'end': {
                    'dateTime': event.end_time.isoformat(),
                    'timeZone': config.timezone,
                },
                'attendees': [{'email': email} for email in event.attendees] if event.attendees else [],
            }
            
            if event.location:
                event_body['location'] = event.location
            
            self.service.events().update(
                calendarId=self.calendar_id,
                eventId=event_id,
                body=event_body
            ).execute()
            
            logger.info(f"Event updated successfully: {event_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating calendar event: {e}")
            return False
    
    def delete_event(self, event_id: str) -> bool:
        """Удаление события из календаря"""
        try:
            if not self.service:
                logger.error("Calendar service not initialized")
                return False
            
            logger.info(f"Deleting calendar event: {event_id}")
            
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            
            logger.info(f"Event deleted successfully: {event_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting calendar event: {e}")
            return False
    
    def suggest_meeting_times(self, preferred_date: Optional[datetime] = None, 
                            duration_hours: float = 2.0) -> List[datetime]:
        """Предложение времени для встречи"""
        try:
            logger.info("Suggesting meeting times")
            
            # Если дата не указана, предлагаем на ближайшие дни
            if not preferred_date:
                preferred_date = datetime.now() + timedelta(days=1)
            
            suggested_times = []
            
            # Ищем доступные слоты на указанную дату и следующие несколько дней
            for days_offset in range(7):  # Проверяем следующие 7 дней
                check_date = preferred_date + timedelta(days=days_offset)
                
                # Пропускаем выходные (можно настроить)
                if check_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
                    continue
                
                available_slots = self.get_available_slots(check_date, duration_hours)
                suggested_times.extend(available_slots[:3])  # Максимум 3 слота в день
                
                if len(suggested_times) >= 6:  # Достаточно предложений
                    break
            
            logger.info(f"Suggested {len(suggested_times)} meeting times")
            return suggested_times[:6]  # Возвращаем максимум 6 вариантов
            
        except Exception as e:
            logger.error(f"Error suggesting meeting times: {e}")
            return []
#!/usr/bin/env python3
"""
Тестовый скрипт для проверки всех компонентов Thumbtack Bot
"""

import sys
import os
from datetime import datetime, timedelta
from loguru import logger

# Добавляем путь к модулям
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import config
from models import Lead, Message, CalendarEvent, LeadStatus, MessageType
from thumbtack_client import ThumbtackClient
from gpt_client import GPTClient
from calendar_client import CalendarClient


def test_config():
    """Тест конфигурации"""
    print("🔧 Testing configuration...")

    try:
        print(f"  ✅ Business Name: {config.business_name}")
        print(f"  ✅ Service Type: {config.service_type}")
        print(f"  ✅ Base Price: ${config.base_price}")
        print(f"  ✅ Check Interval: {config.check_interval_minutes} minutes")

        # Проверяем наличие OpenAI API ключа
        if config.openai_api_key and len(config.openai_api_key) > 10:
            print(f"  ✅ OpenAI API Key: {'*' * 10}...{config.openai_api_key[-4:]}")
        else:
            print("  ❌ OpenAI API Key not configured")
            return False

        return True
    except Exception as e:
        print(f"  ❌ Configuration error: {e}")
        return False


def test_thumbtack_client():
    """Тест Thumbtack клиента"""
    print("\n📞 Testing Thumbtack Client...")

    try:
        client = ThumbtackClient()

        # Тест аутентификации
        if client.authenticate():
            print("  ✅ Authentication successful")
        else:
            print("  ❌ Authentication failed")
            return False

        # Тест получения лидов
        leads = client.get_new_leads()
        print(f"  ✅ Found {len(leads)} leads")

        if leads:
            lead = leads[0]
            print(f"    - Sample lead: {lead.customer_name} ({lead.service_category})")

        # Тест получения сообщений
        messages = client.get_new_messages()
        print(f"  ✅ Found {len(messages)} messages")

        return True
    except Exception as e:
        print(f"  ❌ Thumbtack client error: {e}")
        return False


def test_gpt_client():
    """Тест GPT клиента"""
    print("\n🤖 Testing GPT Client...")

    try:
        client = GPTClient()

        # Проверяем что клиент инициализировался
        if not client.client:
            print("  ❌ GPT client not initialized")
            print("    Hint: Check your OpenAI API key")
            return False

        # Проверяем подключение
        print("  🔍 Testing OpenAI connection...")
        if hasattr(client, '_test_connection') and not client._test_connection():
            print("  ❌ Cannot connect to OpenAI API")
            print("    Hint: Check your API key and internet connection")
            return False

        # Создаем тестовый лид
        test_lead = Lead(
            id="test_lead_001",
            customer_name="Jane Smith",
            customer_email="jane@example.com",
            service_category="Home Repairs & Installation",
            description="I need help installing a ceiling fan in my living room.",
            budget_range=(100, 200),
            preferred_date=datetime.now() + timedelta(days=7),
            location="New York, NY"
        )

        # Тест анализа лида
        print("  🔍 Analyzing test lead...")
        analysis = client.analyze_lead(test_lead)

        print(f"    - Sentiment: {analysis.sentiment}")
        print(f"    - Intent: {analysis.intent}")
        print(f"    - Urgency: {analysis.urgency}")
        print(f"    - Suggested price: ${analysis.suggested_price}")
        print(
            f"    - Key requirements: {', '.join(analysis.key_requirements) if analysis.key_requirements else 'None'}")
        print(f"    - Confidence: {analysis.confidence_score:.2f}")

        # Тест генерации ответа
        print("  📝 Generating quote response...")
        quote_response = client.generate_quote_response(test_lead, analysis.suggested_price or 150)
        print(f"    - Response length: {len(quote_response)} characters")
        print(f"    - Sample: {quote_response[:100]}...")

        print("  ✅ GPT client working correctly")
        return True

    except Exception as e:
        print(f"  ❌ GPT client error: {e}")
        print("    Hint: Check your OpenAI API key and internet connection")
        return False


def test_calendar_client():
    """Тест Calendar клиента"""
    print("\n📅 Testing Calendar Client...")

    try:
        client = CalendarClient()

        # Проверяем наличие credentials.json
        if not os.path.exists(config.google_calendar_credentials_file):
            print(f"  ⚠️ Credentials file not found: {config.google_calendar_credentials_file}")
            print("    Please download credentials.json from Google Cloud Console")
            return False

        # Тест аутентификации
        print("  🔐 Authenticating with Google Calendar...")
        if not client.authenticate():
            print("  ❌ Authentication failed")
            print("    Hint: Make sure credentials.json is valid and Calendar API is enabled")
            return False

        print("  ✅ Authentication successful")

        # Тест проверки доступности
        print("  🔍 Checking availability...")
        tomorrow = datetime.now().replace(hour=14, minute=0, second=0, microsecond=0) + timedelta(days=1)
        end_time = tomorrow + timedelta(hours=2)

        is_available = client.check_availability(tomorrow, end_time)
        print(f"    - Tomorrow 2-4 PM available: {is_available}")

        # Тест получения доступных слотов
        print("  📋 Getting available slots...")
        available_slots = client.get_available_slots(tomorrow, duration_hours=2.0)
        print(f"    - Found {len(available_slots)} available slots")

        for i, slot in enumerate(available_slots[:3]):
            print(f"      {i + 1}. {slot.strftime('%A, %B %d at %I:%M %p')}")

        print("  ✅ Calendar client working correctly")
        return True

    except Exception as e:
        print(f"  ❌ Calendar client error: {e}")
        return False


def test_integration():
    """Интеграционный тест"""
    print("\n🔗 Testing Integration...")

    try:
        # Инициализируем все клиенты
        thumbtack = ThumbtackClient()
        gpt = GPTClient()
        calendar = CalendarClient()

        # Аутентификация
        if not thumbtack.authenticate():
            print("  ❌ Thumbtack authentication failed")
            return False

        if not calendar.authenticate():
            print("  ⚠️ Calendar authentication failed - skipping calendar tests")
            calendar = None

        # Получаем лид
        leads = thumbtack.get_new_leads()
        if not leads:
            print("  ⚠️ No leads found for integration test")
            return True

        lead = leads[0]
        print(f"  📋 Processing lead: {lead.customer_name}")

        # Анализируем лид
        analysis = gpt.analyze_lead(lead)
        print(f"    - GPT analysis: {analysis.intent} (${analysis.suggested_price})")

        # Проверяем календарь если доступен
        if calendar and lead.preferred_date:
            available_slots = calendar.get_available_slots(lead.preferred_date)
            print(f"    - Available slots: {len(available_slots)}")

        # Генерируем ответ
        if analysis.suggested_price:
            quote = gpt.generate_quote_response(lead, analysis.suggested_price)
            print(f"    - Generated quote: {len(quote)} characters")

        print("  ✅ Integration test completed successfully")
        return True

    except Exception as e:
        print(f"  ❌ Integration test error: {e}")
        return False


def main():
    """Основная функция тестирования"""
    print("🧪 Starting Thumbtack Bot Tests\n")

    tests = [
        ("Configuration", test_config),
        ("Thumbtack Client", test_thumbtack_client),
        ("GPT Client", test_gpt_client),
        ("Calendar Client", test_calendar_client),
        ("Integration", test_integration)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
        except KeyboardInterrupt:
            print("\n\n⚠️ Tests interrupted by user")
            break
        except Exception as e:
            print(f"  ❌ Unexpected error in {test_name}: {e}")

    print(f"\n📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Your bot is ready to run.")
        print("\nNext steps:")
        print("  - Run: python main.py --once")
        print("  - Or: python main.py --daemon")
    else:
        print("❌ Some tests failed. Please fix the issues before running the bot.")
        print("\nCommon solutions:")
        print("  - Check your .env file configuration")
        print("  - Verify OpenAI API key is valid")
        print("  - Download credentials.json for Google Calendar API")
        print("  - Ensure internet connection is working")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
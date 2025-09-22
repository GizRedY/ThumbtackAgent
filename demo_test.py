#!/usr/bin/env python3
"""
Демонстрация работы бота с короткими сообщениями клиентов
"""

import sys
import os
from datetime import datetime, timedelta
from loguru import logger

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import config
from models import Lead, Message, MessageType
from thumbtack_client import ThumbtackClient
from gpt_client import GPTClient
from calendar_client import CalendarClient


def print_separator(title=""):
    print("\n" + "=" * 60)
    if title:
        print(f" {title} ".center(60, "="))
        print("=" * 60)


def demo_ai_responses():
    """Демонстрация ответов ИИ на короткие сообщения"""
    print("🤖 ДЕМОНСТРАЦИЯ: Как ИИ отвечает на короткие сообщения клиентов")
    print("Тестируем реакцию ChatGPT на минимальную информацию от клиентов\n")

    # Инициализируем клиентов
    thumbtack = ThumbtackClient()
    gpt = GPTClient()
    calendar_client = CalendarClient()

    # Проверяем что всё работает
    if not thumbtack.authenticate():
        print("❌ Ошибка подключения к Thumbtack")
        return

    if not gpt.is_available():
        print("❌ ИИ недоступен")
        return

    if not calendar_client.authenticate():
        print("⚠️ Календарь недоступен, но продолжаем без него")
        calendar_client = None

    # Получаем тестовых клиентов
    leads = thumbtack.get_new_leads()
    messages = thumbtack.get_new_messages()

    if len(leads) < 2:
        print("❌ Недостаточно тестовых клиентов")
        return

    print(f"✅ Найдено {len(leads)} клиентов и {len(messages)} сообщений\n")

    # Обрабатываем каждого клиента
    for i, lead in enumerate(leads[:2], 1):
        print_separator(f"КЛИЕНТ {i}: {lead.customer_name}")

        print(f"📋 Информация о клиенте:")
        print(f"   Имя: {lead.customer_name}")
        print(f"   Email: {lead.customer_email}")
        print(f"   Описание: '{lead.description}'")  # Это короткое описание
        print(f"   Бюджет: ${lead.budget_range[0]}-${lead.budget_range[1]}")
        print(f"   Предпочтительная дата: {lead.preferred_date}")

        # Ищем сообщение от этого клиента
        client_message = None
        for msg in messages:
            if msg.lead_id == lead.id:
                client_message = msg
                break

        if client_message:
            print(f"\n💬 Сообщение от клиента:")
            print(f"   '{client_message.content}'")
            print(f"   (Длина: {len(client_message.content)} символов)")

        # ИИ анализирует лид
        print(f"\n🧠 ИИ анализирует клиента...")
        analysis = gpt.analyze_lead(lead)

        print(f"   🎯 Настроение: {analysis.sentiment}")
        print(f"   🎯 Намерение: {analysis.intent}")
        print(f"   🎯 Срочность: {analysis.urgency}")
        print(f"   💰 Предлагаемая цена: ${analysis.suggested_price or 'Не указана'}")
        print(
            f"   🔑 Ключевые требования: {', '.join(analysis.key_requirements) if analysis.key_requirements else 'Нет'}")
        print(f"   📊 Уверенность ИИ: {analysis.confidence_score:.1%}")

        # Если есть сообщение, анализируем и его
        if client_message:
            print(f"\n🧠 ИИ анализирует сообщение...")
            msg_analysis = gpt.analyze_message(client_message, lead)
            print(f"   📝 Тип сообщения: {msg_analysis.intent}")
            print(f"   📝 Настроение: {msg_analysis.sentiment}")

        # Генерируем ответ
        suggested_price = analysis.suggested_price or config.base_price
        print(f"\n✍️ ИИ генерирует персональный ответ...")

        # Добавляем контекст из сообщения
        additional_context = ""
        if client_message:
            additional_context = f"Customer message: '{client_message.content}'"

        ai_response = gpt.generate_quote_response(
            lead,
            suggested_price,
            additional_context
        )

        print(f"\n📨 ОТВЕТ ОТ ИИ КЛИЕНТУ:")
        print("-" * 50)
        print(ai_response)
        print("-" * 50)
        print(f"Длина ответа: {len(ai_response)} символов")

        # Проверяем доступность в календаре
        if calendar_client and lead.preferred_date:
            print(f"\n📅 Проверяем доступность в календаре...")

            try:
                # Правильно обрабатываем дату
                if isinstance(lead.preferred_date, str):
                    # Если дата пришла как строка из JSON
                    preferred = datetime.fromisoformat(lead.preferred_date.replace('Z', ''))
                else:
                    # Если это уже datetime объект
                    preferred = lead.preferred_date

                available_slots = calendar_client.get_available_slots(preferred, duration_hours=2.0)

                if available_slots:
                    print(f"   ✅ Найдено {len(available_slots)} свободных слотов")
                    print("   📅 Ближайшие варианты:")
                    for j, slot in enumerate(available_slots[:3], 1):
                        print(f"      {j}. {slot.strftime('%A, %B %d at %I:%M %p')}")
                else:
                    print("   ⚠️ Нет доступных слотов в предпочтительное время")
            except Exception as e:
                print(f"   ❌ Ошибка проверки календаря: {e}")
                # Показываем доступные слоты на завтра вместо ошибки
                try:
                    tomorrow = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
                    available_slots = calendar_client.get_available_slots(tomorrow, duration_hours=2.0)
                    if available_slots:
                        print(f"   📅 Но вот что доступно завтра:")
                        for j, slot in enumerate(available_slots[:2], 1):
                            print(f"      {j}. {slot.strftime('%A, %B %d at %I:%M %p')}")
                except:
                    print("   📅 Календарь временно недоступен")

        # Имитируем отправку ответа
        print(f"\n📤 Отправляем ответ клиенту...")
        success = thumbtack.send_message(lead.id, ai_response)
        if success:
            print("   ✅ Ответ отправлен успешно!")
        else:
            print("   ❌ Ошибка отправки")

        if i < len(leads):
            input(f"\n⏸️  Нажми ENTER чтобы перейти к следующему клиенту...")

    print_separator("ИТОГИ ДЕМОНСТРАЦИИ")
    print("🎉 Демонстрация завершена!")
    print("\n📋 Что мы увидели:")
    print("   • ИИ понимает даже очень короткие описания")
    print("   • Автоматически определяет тип работы и срочность")
    print("   • Генерирует персональные ответы для каждого клиента")
    print("   • Предлагает разумные цены на основе контекста")
    print("   • Учитывает доступность в календаре")
    print("\n🚀 Бот готов к работе с реальными клиентами!")


def quick_analysis_demo():
    """Быстрая демонстрация анализа"""
    print("⚡ БЫСТРЫЙ ТЕСТ: Анализ коротких сообщений")

    gpt = GPTClient()

    if not gpt.is_available():
        print("❌ ИИ недоступен")
        return

    # Тестовые короткие сообщения
    test_cases = [
        ("Outlet issue", "Electrical"),
        ("Fan installation", "Installation"),
        ("Leaky faucet", "Plumbing"),
        ("TV mount", "Installation"),
        ("Light switch broken", "Electrical")
    ]

    print("\n🧪 Тестируем понимание коротких фраз...")

    for description, category in test_cases:
        # Создаём минимальный лид
        test_lead = Lead(
            id=f"test_{description.replace(' ', '_')}",
            customer_name="Test Customer",
            customer_email="test@example.com",
            service_category=category,
            description=description,
            budget_range=(50, 200)
        )

        print(f"\n📝 Фраза: '{description}'")
        analysis = gpt.analyze_lead(test_lead)
        print(f"   🎯 Понял как: {analysis.intent}")
        print(f"   💰 Цена: ${analysis.suggested_price or config.base_price}")
        print(f"   🔑 Требования: {', '.join(analysis.key_requirements[:2]) if analysis.key_requirements else 'Нет'}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--quick', action='store_true', help='Быстрый тест')
    parser.add_argument('--full', action='store_true', help='Полная демонстрация')
    args = parser.parse_args()

    if args.quick:
        quick_analysis_demo()
    elif args.full:
        demo_ai_responses()
    else:
        print("Выбери режим:")
        print("  python demo_test.py --quick   # Быстрый тест")
        print("  python demo_test.py --full    # Полная демонстрация")
        print()
        choice = input("Полная демонстрация? (y/n): ").lower()
        if choice in ['y', 'yes', 'да', '']:
            demo_ai_responses()
        else:
            quick_analysis_demo()
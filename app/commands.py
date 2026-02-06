import asyncio
import re
import os
from datetime import datetime
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    ConversationHandler
)
from telegram.constants import ParseMode

from app.config import settings, logger
from app.database import db_manager
from app.mistral_analyzer import mistral_analyzer
from app.document_generator import document_generator
from app.utils import format_number, validate_inn, get_partner_type_emoji

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    welcome_text = f"""
🤖 *Business Intelligence Partner Bot*

Привет, {user.first_name}! Я помогу вам анализировать бизнес-партнеров.

*Доступные команды:*
/start - Начало работы
/help - Справка по командам
/search <название> - Поиск партнеров
/stats - Статистика системы
/health - Проверка состояния

*Как использовать:*
1. Отправьте мне ИНН партнера (10 или 12 цифр)
2. Получите полную информацию о партнере
3. Запросите аналитический отчет от AI
4. Скачайте детальный отчет в Word формате

*Примеры ИНН для теста:*
• 7707049388 - Global Tech Solutions
• 7830002293 - Eco Manufacturing
• 5001007322 - Logistics Worldwide

*Просто отправьте ИНН для начала анализа!*
    """

    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)

    db_manager.log_interaction(
        user_data={
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name
        },
        action_data={
            'action_type': 'start',
            'response_time_ms': 0,
            'success': True
        }
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📋 *Справка по командам Business Intelligence Bot*

*Основные команды:*
/start - Начало работы с ботом
/help - Эта справка
/search <название> - Поиск партнеров по названию
/stats - Статистика системы и партнеров
/health - Проверка состояния всех сервисов

*Работа с партнерами:*
1. Отправьте ИНН партнера (10 или 12 цифр)
2. Бот найдет информацию в базе данных
3. Вы получите:
   • Основную информацию о партнере
   • Финансовые показатели
   • AI-анализ через Mistral
   • Возможность скачать Word отчет

*Формат ИНН:*
• Юридические лица: 10 цифр
• Физические лица/ИП: 12 цифр

*Примеры использования:*
• Отправьте: `7707049388`
• Поиск: `/search Global Tech`
• Статистика: `/stats`

*Поддерживаемые форматы отчетов:*
• Word (.docx) - Полный детальный отчет
• AI анализ - Оценка рисков и рекомендации

*Техническая информация:*
• Использует Mistral AI для анализа
• Хранит данные в MySQL базе
• Кэширует запросы в Redis
• Генерирует профессиональные отчеты
    """

    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "❌ *Укажите поисковый запрос!*\n\n"
            "Пример: `/search Global Tech`\n"
            "Или: `/search 7707`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    search_query = ' '.join(context.args)
    user = update.effective_user

    await update.message.reply_text(
        f"🔍 *Ищу партнеров по запросу:* `{search_query}`",
        parse_mode=ParseMode.MARKDOWN
    )

    start_time = datetime.now()

    try:
        results = db_manager.search_partners(search_query)

        if not results:
            await update.message.reply_text(
                "❌ *Партнеры не найдены!*\n\n"
                "Попробуйте:\n"
                "• Использовать другое название\n"
                "• Поискать по ИНН\n"
                "• Проверить правильность написания",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        response = f"✅ *Найдено партнеров:* {len(results)}\n\n"

        for i, partner in enumerate(results, 1):
            response += (
                f"*{i}. {partner.get('trade_name') or partner.get('legal_name')}*\n"
                f"   📝 ИНН: `{partner.get('inn')}`\n"
                f"   📋 Тип: {partner.get('partner_type', 'N/A')}\n"
                f"   🏷️ Категория: {partner.get('category', 'N/A')}\n"
                f"   ⭐ Рейтинг: {partner.get('rating', 'N/A')}/5\n\n"
            )

        response += (
            "💡 *Как получить подробную информацию:*\n"
            "Отправьте ИНН партнера для получения полных данных."
        )

        await update.message.reply_text(
            response,
            parse_mode=ParseMode.MARKDOWN
        )

        response_time = (datetime.now() - start_time).total_seconds() * 1000

        db_manager.log_interaction(
            user_data={
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name
            },
            action_data={
                'action_type': 'search',
                'search_query': search_query,
                'response_time_ms': response_time,
                'success': True
            }
        )

    except Exception as e:
        logger.error(f"Error in search command: {e}")

        await update.message.reply_text(
            "❌ *Ошибка при поиске!*\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode=ParseMode.MARKDOWN
        )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    await update.message.reply_text(
        "📊 *Собираю статистику системы...*",
        parse_mode=ParseMode.MARKDOWN
    )

    try:
        stats = db_manager.get_partner_statistics()

        response = "📈 *Статистика Business Intelligence Bot*\n\n"

        response += "👥 *Партнеры:*\n"
        response += f"• Всего партнеров: {stats.get('total_partners', 0)}\n"

        if stats.get('partner_types'):
            response += "• Распределение по типам:\n"
            for p_type, count in stats.get('partner_types', {}).items():
                emoji = get_partner_type_emoji(p_type)
                response += f"  {emoji} {p_type}: {count}\n"

        avg_rating = stats.get('average_rating', 0)
        response += f"• Средний рейтинг: {avg_rating:.1f}/5\n\n"

        reports = stats.get('generated_reports', {})
        response += "📄 *Сгенерированные отчеты:*\n"
        response += f"• Всего отчетов: {reports.get('total', 0)}\n"
        response += f"• Скачано: {reports.get('downloaded', 0)}\n\n"

        recent = stats.get('recent_interactions', [])
        if recent:
            response += "🕐 *Последние действия:*\n"
            for i, action in enumerate(recent[:5], 1):
                user_name = action.get('user', 'Unknown')
                action_type = action.get('action', 'unknown')
                time_str = action.get('time', '').split('T')[0]
                response += f"{i}. {user_name} - {action_type} ({time_str})\n"

        await update.message.reply_text(
            response,
            parse_mode=ParseMode.MARKDOWN
        )

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        await update.message.reply_text(
            "❌ *Ошибка получения статистики!*",
            parse_mode=ParseMode.MARKDOWN
        )

async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        health_status = db_manager.health_check()

        response = "🏥 *Проверка состояния системы*\n\n"

        mysql_status = "✅ Работает" if health_status.get('mysql') else "❌ Ошибка"
        response += f"• База данных MySQL: {mysql_status}\n"

        redis_status = "✅ Работает" if health_status.get('redis') else "❌ Ошибка"
        response += f"• Кэш Redis: {redis_status}\n"

        mistral_status = "✅ Настроен"
        try:
            from mistralai import Mistral
            client = Mistral(api_key=settings.mistral_api_key)
            client.chat.complete(
                model="mistral-tiny",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1
            )
            response += f"• Mistral AI: {mistral_status}\n"
        except:
            response += "• Mistral AI: ⚠️ Проверка не удалась\n"

        timestamp = health_status.get('timestamp', '')
        if timestamp:
            from datetime import datetime
            check_time = datetime.fromisoformat(timestamp)
            response += f"\n🕐 *Последняя проверка:* {check_time.strftime('%H:%M:%S')}\n"

        response += f"\n📊 *Версия бота:* 1.0.0\n"
        response += f"🔧 *Режим:* {'Production' if settings.is_production else 'Development'}\n"

        await update.message.reply_text(
            response,
            parse_mode=ParseMode.MARKDOWN
        )

    except Exception as e:
        logger.error(f"Health check error: {e}")

        await update.message.reply_text(
            "❌ *Ошибка проверки состояния системы!*",
            parse_mode=ParseMode.MARKDOWN
        )

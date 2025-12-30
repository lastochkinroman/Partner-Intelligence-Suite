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
from app.utils import format_number, validate_inn, format_partner_summary, calculate_growth

async def handle_inn_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    inn_text = update.message.text.strip()
    user = update.effective_user

    start_time = datetime.now()

    if not validate_inn(inn_text):
        await update.message.reply_text(
            "❌ *Неверный формат ИНН!*\n\n"
            "ИНН должен содержать:\n"
            "• 10 цифр для юридических лиц\n"
            "• 12 цифр для ИП/физических лиц\n\n"
            "Пожалуйста, проверьте и отправьте корректный ИНН.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    await update.message.reply_text(
        f"🔍 *Ищу информацию по ИНН:* `{inn_text}`",
        parse_mode=ParseMode.MARKDOWN
    )

    try:
        partner_data = db_manager.get_partner_by_inn(inn_text)

        if not partner_data:
            await update.message.reply_text(
                f"❌ *Партнер с ИНН `{inn_text}` не найден.*\n\n"
                "Возможные причины:\n"
                "• Партнер не зарегистрирован в базе\n"
                "• Проверьте корректность ИНН\n"
                "• Используйте команду /search для поиска по названию",
                parse_mode=ParseMode.MARKDOWN
            )

            db_manager.log_interaction(
                user_data={
                    'id': user.id,
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name
                },
                action_data={
                    'action_type': 'search_by_inn',
                    'partner_inn': inn_text,
                    'response_time_ms': (datetime.now() - start_time).total_seconds() * 1000,
                    'success': False,
                    'error_message': 'Partner not found'
                }
            )
            return

        response_time = (datetime.now() - start_time).total_seconds() * 1000

        summary_text = format_partner_summary(partner_data)

        contacts = partner_data.get('contacts', {})
        if contacts.get('ceo') or contacts.get('cfo'):
            summary_text += "\n\n👥 *Руководство:*"
            if contacts.get('ceo'):
                summary_text += f"\n• Ген. директор: {contacts.get('ceo')}"
            if contacts.get('cfo'):
                summary_text += f"\n• Фин. директор: {contacts.get('cfo')}"

        if partner_data.get('website'):
            summary_text += f"\n🌐 *Сайт:* {partner_data.get('website')}"

        keyboard = [
            [
                InlineKeyboardButton("🤖 AI Анализ", callback_data=f"analyze:{inn_text}"),
                InlineKeyboardButton("📄 Отчет Word", callback_data=f"report:{inn_text}")
            ],
            [
                InlineKeyboardButton("📊 Финансы", callback_data=f"finance:{inn_text}"),
                InlineKeyboardButton("📞 Контакты", callback_data=f"contacts:{inn_text}")
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            summary_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

        db_manager.log_interaction(
            user_data={
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name
            },
            action_data={
                'action_type': 'search_by_inn',
                'partner_inn': inn_text,
                'response_time_ms': response_time,
                'success': True
            }
        )

    except Exception as e:
        logger.error(f"Error handling INN input: {e}")

        await update.message.reply_text(
            "❌ *Произошла ошибка при поиске партнера.*\n\n"
            "Пожалуйста, попробуйте позже или обратитесь к администратору.",
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    callback_data = query.data
    user = query.from_user

    if callback_data.startswith('analyze:'):
        inn = callback_data.split(':')[1]
        await handle_ai_analysis(query, user, inn)

    elif callback_data.startswith('report:'):
        inn = callback_data.split(':')[1]
        await handle_report_generation(query, user, inn)

    elif callback_data.startswith('finance:'):
        inn = callback_data.split(':')[1]
        await handle_financial_details(query, user, inn)

    elif callback_data.startswith('contacts:'):
        inn = callback_data.split(':')[1]
        await handle_contact_details(query, user, inn)

async def handle_ai_analysis(query, user, inn: str):
    start_time = datetime.now()

    await query.edit_message_text(
        text=f"🤖 *Запускаю AI анализ партнера...*\n\nИНН: `{inn}`\n\n"
             "⏳ Это займет несколько секунд...",
        parse_mode=ParseMode.MARKDOWN
    )

    try:
        partner_data = db_manager.get_partner_by_inn(inn)
        if not partner_data:
            await query.edit_message_text(
                text=f"❌ *Данные партнера не найдены!*\n\nИНН: `{inn}`",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        analysis_result = await mistral_analyzer.analyze_partner(partner_data)

        if not analysis_result.get('success'):
            await query.edit_message_text(
                text=f"❌ *Ошибка AI анализа!*\n\n"
                     f"ИНН: `{inn}`\n\n"
                     f"Ошибка: {analysis_result.get('error', 'Unknown error')}",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        summary = await mistral_analyzer.generate_partner_summary(
            partner_data,
            analysis_result
        )

        execution_time = analysis_result.get('execution_time_ms', 0)
        summary += f"\n\n⏱️ *Время анализа:* {execution_time:.0f}ms"
        summary += f"\n🤖 *Модель:* {analysis_result.get('model_used')}"

        keyboard = [
            [
                InlineKeyboardButton("📄 Полный отчет Word", callback_data=f"full_report:{inn}"),
                InlineKeyboardButton("📊 Финансовый анализ", callback_data=f"detailed_finance:{inn}")
            ],
            [
                InlineKeyboardButton("◀️ Назад к партнеру", callback_data=f"back:{inn}")
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text=summary,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

        db_manager.log_interaction(
            user_data={
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name
            },
            action_data={
                'action_type': 'ai_analysis',
                'partner_inn': inn,
                'response_time_ms': execution_time,
                'success': True
            }
        )

    except Exception as e:
        logger.error(f"Error in AI analysis: {e}")

        await query.edit_message_text(
            text=f"❌ *Ошибка при выполнении AI анализа!*\n\n"
                 f"ИНН: `{inn}`\n\n"
                 f"Ошибка: {str(e)[:200]}",
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_report_generation(query, user, inn: str):
    start_time = datetime.now()

    await query.edit_message_text(
        text=f"📄 *Начинаю генерацию Word отчета...*\n\n"
             f"ИНН: `{inn}`\n\n"
             f"⏳ Это займет несколько секунд...",
        parse_mode=ParseMode.MARKDOWN
    )

    try:
        partner_data = db_manager.get_partner_by_inn(inn)
        if not partner_data:
            await query.edit_message_text(
                text=f"❌ *Данные партнера не найдены!*\n\nИНН: `{inn}`",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        analysis_result = await mistral_analyzer.analyze_partner(partner_data)

        report_result = document_generator.generate_partner_report(
            partner_data,
            analysis_result
        )

        if not report_result.get('success'):
            await query.edit_message_text(
                text=f"❌ *Ошибка генерации отчета!*\n\n"
                     f"ИНН: `{inn}`\n\n"
                     f"Ошибка: {report_result.get('error', 'Unknown error')}",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        report_uuid = db_manager.save_generated_report({
            'partner_inn': inn,
            'telegram_user_id': user.id,
            'report_type': 'word',
            'report_path': report_result.get('filepath'),
            'file_size_bytes': report_result.get('file_size_bytes'),
            'ai_analysis': analysis_result.get('raw_response'),
            'generation_time_ms': report_result.get('generation_time_ms')
        })

        with open(report_result['filepath'], 'rb') as file:
            await query.message.reply_document(
                document=file,
                filename=report_result['filename'],
                caption=f"📄 *Отчет по партнеру*\n\n"
                        f"🏢 *Компания:* {partner_data.get('trade_name')}\n"
                        f"📝 *ИНН:* `{inn}`\n"
                        f"📊 *Размер файла:* {report_result['file_size_bytes'] / 1024:.1f} KB\n"
                        f"⏱️ *Время генерации:* {report_result['generation_time_ms']:.0f}ms\n"
                        f"🆔 *ID отчета:* `{report_uuid}`",
                parse_mode=ParseMode.MARKDOWN
            )

        await query.edit_message_text(
            text=f"✅ *Отчет успешно сгенерирован!*\n\n"
                 f"ИНН: `{inn}`\n"
                 f"📁 Файл отправлен в чат\n"
                 f"⏱️ Время генерации: {report_result['generation_time_ms']:.0f}ms",
            parse_mode=ParseMode.MARKDOWN
        )

        db_manager.log_interaction(
            user_data={
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name
            },
            action_data={
                'action_type': 'report_generation',
                'partner_inn': inn,
                'response_time_ms': (datetime.now() - start_time).total_seconds() * 1000,
                'success': True
            }
        )

    except Exception as e:
        logger.error(f"Error generating report: {e}")

        await query.edit_message_text(
            text=f"❌ *Ошибка генерации отчета!*\n\n"
                 f"ИНН: `{inn}`\n\n"
                 f"Ошибка: {str(e)[:200]}",
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_financial_details(query, user, inn: str):
    partner_data = db_manager.get_partner_by_inn(inn)

    if not partner_data:
        await query.edit_message_text(
            text=f"❌ *Данные партнера не найдены!*\n\nИНН: `{inn}`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    financials = partner_data.get('financials', {})

    response = f"📊 *Финансовые показатели*\n\n"
    response += f"🏢 *{partner_data.get('trade_name')}*\n"
    response += f"📝 `{inn}`\n\n"

    response += "💰 *Основные показатели:*\n"
    if financials.get('revenue_2023'):
        response += f"• Выручка 2023: {format_number(financials['revenue_2023'])}\n"
    if financials.get('revenue_2022'):
        response += f"• Выручка 2022: {format_number(financials['revenue_2022'])}\n"
    if financials.get('profit_2023'):
        response += f"• Прибыль 2023: {format_number(financials['profit_2023'])}\n"

    if financials.get('revenue_2022') and financials.get('revenue_2023'):
        growth = calculate_growth(
            financials.get('revenue_2023'),
            financials.get('revenue_2022')
        )
        if growth != "N/A":
            response += f"• Рост выручки: {growth}\n"

    turnovers = financials.get('turnovers', [])
    if turnovers:
        response += "\n📈 *Исторические данные об оборотах:*\n"

        years_data = {}
        for t in turnovers:
            year = t.get('year')
            if year not in years_data:
                years_data[year] = []
            years_data[year].append(t)

        for year in sorted(years_data.keys(), reverse=True):
            year_data = years_data[year]
            total_revenue = sum(t.get('revenue', 0) for t in year_data)
            response += f"\n*{year} год:* {format_number(total_revenue)}\n"

            for t in sorted(year_data, key=lambda x: x.get('quarter', 0)):
                quarter = f"Q{t.get('quarter')}" if t.get('quarter') else "Год"
                revenue = format_number(t.get('revenue', 0))
                profit = format_number(t.get('profit', 0)) if t.get('profit') else "N/A"
                response += f"  {quarter}: {revenue} (прибыль: {profit})\n"

    if financials.get('founding_year'):
        response += f"\n📅 *Год основания:* {financials['founding_year']}\n"
    if financials.get('employee_count'):
        response += f"👥 *Сотрудников:* {financials['employee_count']:,}\n"

    keyboard = [
        [
            InlineKeyboardButton("🤖 AI Анализ", callback_data=f"analyze:{inn}"),
            InlineKeyboardButton("📄 Отчет Word", callback_data=f"report:{inn}")
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data=f"back:{inn}")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=response,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def handle_contact_details(query, user, inn: str):
    partner_data = db_manager.get_partner_by_inn(inn)

    if not partner_data:
        await query.edit_message_text(
            text=f"❌ *Данные партнера не найдены!*\n\nИНН: `{inn}`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    response = f"📞 *Контактная информация*\n\n"
    response += f"🏢 *{partner_data.get('trade_name')}*\n"
    response += f"📝 `{inn}`\n\n"

    contacts = partner_data.get('contacts', {})
    addresses = partner_data.get('addresses', [])

    if contacts.get('ceo') or contacts.get('cfo'):
        response += "👥 *Руководство:*\n"
        if contacts.get('ceo'):
            response += f"• Генеральный директор: {contacts['ceo']}\n"
        if contacts.get('cfo'):
            response += f"• Финансовый директор: {contacts['cfo']}\n"
        response += "\n"

    response += "📱 *Контакты:*\n"
    if contacts.get('email'):
        response += f"• Email: {contacts['email']}\n"
    if contacts.get('phone'):
        response += f"• Телефон: {contacts['phone']}\n"

    if partner_data.get('website'):
        response += f"• Веб-сайт: {partner_data['website']}\n"

    if addresses:
        response += "\n🏢 *Адреса:*\n"
        for i, address in enumerate(addresses, 1):
            response += f"{i}. {address}\n"

    keyboard = [
        [
            InlineKeyboardButton("📊 Финансы", callback_data=f"finance:{inn}"),
            InlineKeyboardButton("🤖 AI Анализ", callback_data=f"analyze:{inn}")
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data=f"back:{inn}")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=response,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

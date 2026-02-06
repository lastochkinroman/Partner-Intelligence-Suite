import re
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import hashlib
from functools import wraps
import time
from app.config import logger

def validate_inn(inn: str) -> bool:
    if not inn or not inn.isdigit():
        return False

    inn = inn.strip()

    if len(inn) not in (10, 12):
        return False

    if len(inn) == 10:
        coefficients = [2, 4, 10, 3, 5, 9, 4, 6, 8]
        check_sum = sum(int(inn[i]) * coefficients[i] for i in range(9))
        check_digit = (check_sum % 11) % 10
        return int(inn[9]) == check_digit

    else:
        coefficients1 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        check_sum1 = sum(int(inn[i]) * coefficients1[i] for i in range(10))
        check_digit1 = (check_sum1 % 11) % 10

        coefficients2 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        check_sum2 = sum(int(inn[i]) * coefficients2[i] for i in range(11))
        check_digit2 = (check_sum2 % 11) % 10

        return int(inn[10]) == check_digit1 and int(inn[11]) == check_digit2

def format_number(number: float) -> str:
    if number is None:
        return "N/A"

    if number >= 1_000_000_000:
        return f"${number/1_000_000_000:.2f}B"
    elif number >= 1_000_000:
        return f"${number/1_000_000:.2f}M"
    elif number >= 1_000:
        return f"${number/1_000:.2f}K"
    else:
        return f"${number:.2f}"

def calculate_growth(current: float, previous: float) -> str:
    if previous == 0 or previous is None or current is None:
        return "N/A"

    growth = ((current - previous) / previous) * 100

    if growth > 0:
        return f"↑ {growth:.1f}%"
    elif growth < 0:
        return f"↓ {abs(growth):.1f}%"
    else:
        return "0.0%"

def safe_json_loads(data: str) -> Dict:
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return {}

def format_datetime(dt: Optional[datetime]) -> str:
    if not dt:
        return "N/A"

    return dt.strftime("%d.%m.%Y %H:%M")

def get_partner_type_emoji(partner_type: str) -> str:
    emoji_map = {
        'strategic': '🏆',
        'current': '✅',
        'potential': '🔍',
        'blocked': '🚫',
        'vip': '⭐'
    }
    return emoji_map.get(partner_type, '📊')

def get_risk_level_emoji(risk_level: str) -> str:
    emoji_map = {
        'Low': '🟢',
        'Medium': '🟡',
        'High': '🟠',
        'Critical': '🔴'
    }
    return emoji_map.get(risk_level, '⚪')

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def cache_key_generator(func_name: str, *args, **kwargs) -> str:
    key_parts = [func_name]

    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            key_parts.append(str(arg))

    for key, value in kwargs.items():
        if key not in ['self', 'cls']:
            key_parts.append(f"{key}:{value}")

    key_string = ":".join(key_parts)
    return f"cache:{hashlib.md5(key_string.encode()).hexdigest()}"

def timing_decorator(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = (time.time() - start_time) * 1000
            logger.debug(f"{func.__name__} executed in {execution_time:.2f}ms")
            return result
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"{func.__name__} failed after {execution_time:.2f}ms: {e}")
            raise
    return wrapper

def format_partner_summary(partner_data: Dict[str, Any]) -> str:
    summary = []

    summary.append(f"🏢 *{partner_data.get('trade_name', partner_data.get('legal_name'))}*")
    summary.append(f"📝 `{partner_data.get('inn')}`")

    partner_type = partner_data.get('partner_type', '').title()
    summary.append(f"📋 {get_partner_type_emoji(partner_type)} Тип: {partner_type}")

    if partner_data.get('category'):
        summary.append(f"🏷️ Категория: {partner_data.get('category')}")

    financials = partner_data.get('financials', {})
    if financials.get('revenue_2023'):
        revenue = format_number(financials.get('revenue_2023'))
        summary.append(f"💰 Выручка 2023: {revenue}")

    if financials.get('revenue_2022') and financials.get('revenue_2023'):
        growth = calculate_growth(
            financials.get('revenue_2023'),
            financials.get('revenue_2022')
        )
        if growth != "N/A":
            summary.append(f"📈 Рост выручки: {growth}")

    ratings = partner_data.get('ratings', {})
    if ratings.get('rating'):
        summary.append(f"⭐ Рейтинг: {ratings.get('rating')}/5")

    if ratings.get('risk_level'):
        risk_emoji = get_risk_level_emoji(ratings.get('risk_level'))
        summary.append(f"⚠️ Риск: {risk_emoji} {ratings.get('risk_level')}")

    return "\n".join(summary)

def clean_filename(filename: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]', '_', filename)
    cleaned = cleaned.strip(' .')
    return cleaned[:100]

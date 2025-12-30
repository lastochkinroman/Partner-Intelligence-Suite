from typing import Dict, Any, Optional
import asyncio
from datetime import datetime
import json

from mistralai import Mistral
from app.config import settings, logger
from app.database import db_manager

class MistralAnalyzer:
    

    def __init__(self):
        self.client = Mistral(api_key=settings.mistral_api_key)
        self.model = settings.mistral_model
        self.temperature = settings.mistral_temperature

    async def analyze_partner(self, partner_data: Dict[str, Any]) -> Dict[str, Any]:
        
        start_time = datetime.now()

        try:
            system_prompt = """Ты - эксперт по бизнес-анализу. Проанализируй данные партнера и предоставь анализ в формате JSON со следующими разделами:
- financial_analysis: финансовый анализ
- risk_assessment: оценка рисков с уровнем (Low/Medium/High), факторами и рекомендациями
- partnership_potential: потенциал партнерства с оценкой (1-10), возможностями и угрозами
- strategic_recommendations: стратегические рекомендации
- summary: краткое резюме"""

            partner_info = f"""Название: {partner_data.get('trade_name', 'N/A')}
ИНН: {partner_data.get('inn', 'N/A')}
ОГРН: {partner_data.get('ogrn', 'N/A')}
Адрес: {partner_data.get('address', 'N/A')}
Статус: {partner_data.get('status', 'N/A')}
Финансовые показатели: {partner_data.get('financial_data', {})}
История: {partner_data.get('history', 'N/A')}"""

            response = self.client.chat.complete(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Проанализируй этого партнера:\n\n{partner_info}"}
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )

            analysis_text = response.choices[0].message.content
            analysis_data = json.loads(analysis_text)

            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            result = {
                "analysis": analysis_data,
                "raw_response": analysis_text,
                "execution_time_ms": round(execution_time, 2),
                "model_used": self.model,
                "timestamp": datetime.now().isoformat(),
                "success": True
            }

            logger.info(f"✅ Partner analysis completed in {execution_time:.2f}ms")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error in analysis: {e}")
            return {
                "analysis": {
                    "financial_analysis": {"error": "Failed to parse analysis"},
                    "risk_assessment": {"level": "Unknown", "factors": [], "recommendations": []},
                    "partnership_potential": {"score": 5, "opportunities": [], "threats": []},
                    "strategic_recommendations": ["Требуется ручной анализ данных"],
                    "summary": "Не удалось автоматически проанализировать данные партнера"
                },
                "execution_time_ms": round((datetime.now() - start_time).total_seconds() * 1000, 2),
                "error": str(e),
                "success": False
            }
        except Exception as e:
            logger.error(f"Mistral AI analysis error: {e}")
            return {
                "analysis": {
                    "financial_analysis": {"error": "Analysis failed"},
                    "risk_assessment": {"level": "Unknown", "factors": [], "recommendations": []},
                    "partnership_potential": {"score": 5, "opportunities": [], "threats": []},
                    "strategic_recommendations": ["Требуется ручной анализ"],
                    "summary": "Ошибка при анализе данных"
                },
                "execution_time_ms": round((datetime.now() - start_time).total_seconds() * 1000, 2),
                "error": str(e),
                "success": False
            }

    async def generate_partner_summary(self, partner_data: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        
        try:
            summary_prompt = f"""Создай краткое резюме для партнера на основе следующих данных:

Партнер: {partner_data.get('trade_name', 'N/A')}
Анализ: {json.dumps(analysis, ensure_ascii=False, indent=2)}

Резюме должно быть структурированным и подходящим для бизнес-отчета."""

            response = self.client.chat.complete(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Ты создаешь краткие, структурированные резюме для бизнес-отчетов."},
                    {"role": "user", "content": summary_prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return f"🏢 *{partner_data.get('trade_name')}*\n\n📊 Основные показатели доступны в полном отчете."

mistral_analyzer = MistralAnalyzer()

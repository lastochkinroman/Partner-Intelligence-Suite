import redis
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager
from typing import Generator, Optional, Dict, Any
import json
import time
from datetime import datetime, timedelta

from app.config import settings, logger
from app.models import Base, Partner, Turnover, BotInteraction, GeneratedReport

class DatabaseManager:
    

    def __init__(self):
        self.engine = create_engine(
            settings.mysql_connection_string,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=settings.app_debug
        )

        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

        self.redis_client = redis.Redis.from_url(
            settings.redis_connection_string,
            decode_responses=True
        )

        self.init_database()

    def init_database(self):
        
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("✅ Database tables created successfully")

            self.redis_client.ping()
            logger.info("✅ Redis connection established")

        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    def get_partner_by_inn(self, inn: str) -> Optional[Dict[str, Any]]:
        
        cache_key = f"partner:{inn}"

        cached_data = self.redis_client.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for partner {inn}")
            return json.loads(cached_data)

        try:
            with self.get_session() as session:
                partner = session.query(Partner).filter(Partner.inn == inn).first()

                if not partner:
                    return None

                turnovers = session.query(Turnover).filter(
                    Turnover.partner_inn == inn
                ).order_by(Turnover.year.desc(), Turnover.quarter.desc()).all()

                partner_data = {
                    'inn': partner.inn,
                    'legal_name': partner.legal_name,
                    'trade_name': partner.trade_name,
                    'partner_type': partner.partner_type.value,
                    'category': partner.category,
                    'competitor': partner.competitor,

                    'contacts': {
                        'email': partner.email,
                        'phone': partner.phone,
                        'ceo': partner.ceo_name,
                        'cfo': partner.cfo_name
                    },
                    'website': partner.website,
                    'addresses': partner.addresses if partner.addresses else [],

                    'financials': {
                        'revenue_2023': partner.revenue_2023,
                        'revenue_2022': partner.revenue_2022,
                        'profit_2023': partner.profit_2023,
                        'founding_year': partner.founding_year,
                        'employee_count': partner.employee_count,
                        'turnovers': [
                            {
                                'year': t.year,
                                'quarter': t.quarter,
                                'revenue': t.revenue,
                                'profit': t.profit,
                                'transaction_count': t.transaction_count,
                                'average_transaction': t.average_transaction
                            }
                            for t in turnovers
                        ]
                    },

                    'codes': {
                        'industry': partner.industry_code,
                        'okved': partner.okved_code
                    },

                    'ratings': {
                        'rating': partner.rating,
                        'risk_level': partner.risk_level.value,
                        'payment_terms': partner.payment_terms
                    },

                    'metadata': {
                        'last_audit': partner.last_audit_date.isoformat() if partner.last_audit_date else None,
                        'created_at': partner.created_at.isoformat(),
                        'updated_at': partner.updated_at.isoformat()
                    }
                }

                self.redis_client.setex(
                    cache_key,
                    settings.cache_ttl_seconds,
                    json.dumps(partner_data, default=str)
                )

                return partner_data

        except SQLAlchemyError as e:
            logger.error(f"Database error fetching partner {inn}: {e}")
            return None

    def log_interaction(self, user_data: Dict[str, Any], action_data: Dict[str, Any]):
        
        try:
            with self.get_session() as session:
                interaction = BotInteraction(
                    telegram_user_id=user_data.get('id'),
                    telegram_username=user_data.get('username'),
                    telegram_first_name=user_data.get('first_name'),
                    telegram_last_name=user_data.get('last_name'),
                    action_type=action_data.get('action_type'),
                    partner_inn=action_data.get('partner_inn'),
                    search_query=action_data.get('search_query'),
                    response_time_ms=action_data.get('response_time_ms'),
                    success=action_data.get('success', True),
                    error_message=action_data.get('error_message')
                )
                session.add(interaction)

        except Exception as e:
            logger.error(f"Error logging interaction: {e}")

    def save_generated_report(self, report_data: Dict[str, Any]) -> str:
        
        try:
            import uuid

            report_uuid = str(uuid.uuid4())

            with self.get_session() as session:
                report = GeneratedReport(
                    report_uuid=report_uuid,
                    partner_inn=report_data.get('partner_inn'),
                    telegram_user_id=report_data.get('telegram_user_id'),
                    report_type=report_data.get('report_type', 'word'),
                    report_path=report_data.get('report_path'),
                    file_size_bytes=report_data.get('file_size_bytes'),
                    ai_analysis=report_data.get('ai_analysis'),
                    generation_time_ms=report_data.get('generation_time_ms')
                )
                session.add(report)

            return report_uuid

        except Exception as e:
            logger.error(f"Error saving report: {e}")
            return ""

    def increment_report_download(self, report_uuid: str):
        
        try:
            with self.get_session() as session:
                report = session.query(GeneratedReport).filter(
                    GeneratedReport.report_uuid == report_uuid
                ).first()

                if report:
                    report.downloaded = True
                    report.download_count += 1
                    report.last_downloaded_at = datetime.now()

        except Exception as e:
            logger.error(f"Error incrementing report download: {e}")

    def get_partner_statistics(self, days: int = 30) -> Dict[str, Any]:
        
        cache_key = f"stats:partners:{days}"

        cached_data = self.redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)

        try:
            with self.get_session() as session:
                total_partners = session.query(Partner).count()

                partner_types = session.execute(text()).fetchall()

                avg_rating = session.query(func.avg(Partner.rating)).scalar()

                recent_interactions = session.query(BotInteraction).order_by(
                    BotInteraction.created_at.desc()
                ).limit(10).all()

                stats = {
                    'total_partners': total_partners,
                    'partner_types': {pt[0]: pt[1] for pt in partner_types},
                    'average_rating': float(avg_rating) if avg_rating else 0,
                    'recent_interactions': [
                        {
                            'user': f"{i.telegram_first_name} {i.telegram_last_name or ''}".strip(),
                            'action': i.action_type,
                            'time': i.created_at.isoformat()
                        }
                        for i in recent_interactions
                    ],
                    'generated_reports': {
                        'total': session.query(GeneratedReport).count(),
                        'downloaded': session.query(GeneratedReport).filter(
                            GeneratedReport.downloaded == True
                        ).count()
                    }
                }

                self.redis_client.setex(cache_key, 300, json.dumps(stats, default=str))

                return stats

        except Exception as e:
            logger.error(f"Error fetching partner statistics: {e}")
            return {}

    def search_partners(self, query: str, limit: int = 10) -> list:
        
        cache_key = f"search:{query}:{limit}"

        cached_data = self.redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)

        try:
            with self.get_session() as session:
                inn_results = session.query(Partner).filter(
                    Partner.inn.like(f"%{query}%")
                ).limit(limit).all()

                name_results = session.query(Partner).filter(
                    Partner.legal_name.like(f"%{query}%") |
                    Partner.trade_name.like(f"%{query}%")
                ).limit(limit).all()

                all_results = {p.inn: p for p in inn_results + name_results}
                results = list(all_results.values())[:limit]

                formatted_results = [
                    {
                        'inn': p.inn,
                        'legal_name': p.legal_name,
                        'trade_name': p.trade_name,
                        'category': p.category,
                        'partner_type': p.partner_type.value,
                        'rating': p.rating
                    }
                    for p in results
                ]

                self.redis_client.setex(cache_key, 60, json.dumps(formatted_results))

                return formatted_results

        except Exception as e:
            logger.error(f"Error searching partners: {e}")
            return []

    def health_check(self) -> Dict[str, Any]:
        
        health_status = {
            'mysql': False,
            'redis': False,
            'timestamp': datetime.now().isoformat()
        }

        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
                health_status['mysql'] = True
        except Exception as e:
            logger.error(f"MySQL health check failed: {e}")

        try:
            self.redis_client.ping()
            health_status['redis'] = True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")

        return health_status

db_manager = DatabaseManager()

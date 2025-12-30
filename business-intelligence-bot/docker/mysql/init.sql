-- Создание базы данных партнеров
CREATE DATABASE IF NOT EXISTS partner_db;
USE partner_db;

-- Таблица партнеров
CREATE TABLE IF NOT EXISTS partners (
    id INT AUTO_INCREMENT PRIMARY KEY,
    inn VARCHAR(20) UNIQUE NOT NULL,
    legal_name VARCHAR(255) NOT NULL,
    trade_name VARCHAR(255),
    partner_type ENUM('strategic', 'current', 'potential', 'blocked', 'vip') DEFAULT 'current',
    category VARCHAR(100),
    competitor VARCHAR(255),

    -- Контактная информация
    email VARCHAR(255),
    phone VARCHAR(50),
    ceo_name VARCHAR(255),
    cfo_name VARCHAR(255),
    website VARCHAR(255),

    -- Адреса (JSON)
    addresses JSON,

    -- Финансовые показатели
    revenue_2023 DECIMAL(15,2),
    revenue_2022 DECIMAL(15,2),
    profit_2023 DECIMAL(15,2),
    founding_year INT,
    employee_count INT,

    -- Коды и классификации
    industry_code VARCHAR(10),
    okved_code VARCHAR(20),

    -- Рейтинги и оценки
    rating DECIMAL(3,2),
    risk_level ENUM('Low', 'Medium', 'High', 'Critical'),
    payment_terms VARCHAR(50),

    -- Метаданные
    last_audit_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_inn (inn),
    INDEX idx_partner_type (partner_type),
    INDEX idx_category (category),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Таблица транзакций/оборотов
CREATE TABLE IF NOT EXISTS turnovers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    partner_inn VARCHAR(20) NOT NULL,
    year INT NOT NULL,
    quarter INT,
    revenue DECIMAL(15,2) NOT NULL,
    profit DECIMAL(15,2),
    transaction_count INT,
    average_transaction DECIMAL(15,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (partner_inn) REFERENCES partners(inn) ON DELETE CASCADE,
    INDEX idx_partner_year (partner_inn, year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Таблица взаимодействий с ботом
CREATE TABLE IF NOT EXISTS bot_interactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    telegram_user_id BIGINT NOT NULL,
    telegram_username VARCHAR(100),
    telegram_first_name VARCHAR(100),
    telegram_last_name VARCHAR(100),

    action_type VARCHAR(50) NOT NULL,  -- search, report_download, analysis_request
    partner_inn VARCHAR(20),
    search_query TEXT,

    response_time_ms INT,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_user_id (telegram_user_id),
    INDEX idx_created_at (created_at),
    INDEX idx_action_type (action_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Таблица сгенерированных отчетов
CREATE TABLE IF NOT EXISTS generated_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    report_uuid VARCHAR(36) UNIQUE NOT NULL,
    partner_inn VARCHAR(20) NOT NULL,
    telegram_user_id BIGINT NOT NULL,

    report_type ENUM('word', 'pdf', 'excel') DEFAULT 'word',
    report_path VARCHAR(500),
    file_size_bytes INT,

    ai_analysis TEXT,
    generation_time_ms INT,

    downloaded BOOLEAN DEFAULT FALSE,
    download_count INT DEFAULT 0,
    last_downloaded_at TIMESTAMP NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (partner_inn) REFERENCES partners(inn) ON DELETE CASCADE,
    INDEX idx_report_uuid (report_uuid),
    INDEX idx_user_partner (telegram_user_id, partner_inn),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Вставка тестовых данных
INSERT INTO partners (
    inn, legal_name, trade_name, partner_type, category, competitor,
    email, phone, ceo_name, cfo_name, website,
    addresses,
    revenue_2023, revenue_2022, profit_2023, founding_year, employee_count,
    industry_code, okved_code,
    rating, risk_level, payment_terms, last_audit_date
) VALUES
(
    '7707049388',
    'Global Tech Solutions Inc.',
    'Global Tech',
    'current',
    'Technology Partner',
    'Tech Innovations Ltd',
    'partnerships@globaltech.com',
    '+1 800 555-0100',
    'John Anderson',
    'Sarah Johnson',
    'https://globaltech.com',
    '["123 Tech Street, San Francisco, CA 94105", "456 Innovation Ave, Austin, TX 73301"]',
    1250000000.00,
    980000000.00,
    150000000.00,
    2010,
    1250,
    '6201',
    '62.01',
    4.8,
    'Low',
    'Net 30',
    '2023-12-15'
),
(
    '7830002293',
    'Eco Manufacturing Corp.',
    'EcoManufacture',
    'strategic',
    'Manufacturing Partner',
    'Green Industries Inc.',
    'partners@ecomfg.com',
    '+1 312 555-0200',
    'Robert Chen',
    'Maria Garcia',
    'https://ecomfg.com',
    '["789 Industrial Park, Chicago, IL 60607", "101 Green Way, Portland, OR 97201"]',
    890000000.00,
    720000000.00,
    85000000.00,
    2005,
    850,
    '3100',
    '31.00',
    4.6,
    'Medium',
    'Net 45',
    '2024-01-20'
),
(
    '5001007322',
    'Logistics Worldwide Ltd.',
    'LogisticsWorld',
    'current',
    'Logistics Partner',
    'Global Shipping Corp',
    'contact@logisticsworld.com',
    '+1 305 555-0300',
    'Michael Rodriguez',
    'Lisa Wong',
    'https://logisticsworld.com',
    '["555 Harbor Drive, Miami, FL 33132", "222 Port Avenue, Los Angeles, CA 90012"]',
    1500000000.00,
    1350000000.00,
    120000000.00,
    2008,
    2100,
    '4900',
    '49.00',
    4.7,
    'Low',
    'Net 30',
    '2024-02-10'
);

-- Вставка исторических данных об оборотах
INSERT INTO turnovers (partner_inn, year, quarter, revenue, profit, transaction_count, average_transaction) VALUES
('7707049388', 2023, 1, 300000000, 35000000, 45000, 6666.67),
('7707049388', 2023, 2, 310000000, 37000000, 46000, 6739.13),
('7707049388', 2023, 3, 320000000, 39000000, 48000, 6666.67),
('7707049388', 2023, 4, 320000000, 39000000, 49000, 6530.61),

('7830002293', 2023, 1, 210000000, 20000000, 32000, 6562.50),
('7830002293', 2023, 2, 220000000, 21000000, 33000, 6666.67),
('7830002293', 2023, 3, 230000000, 22000000, 34000, 6764.71),
('7830002293', 2023, 4, 230000000, 22000000, 35000, 6571.43),

('5001007322', 2023, 1, 360000000, 28000000, 52000, 6923.08),
('5001007322', 2023, 2, 370000000, 29000000, 53000, 6981.13),
('5001007322', 2023, 3, 380000000, 30000000, 54000, 7037.04),
('5001007322', 2023, 4, 390000000, 33000000, 55000, 7090.91);

-- Создание пользователя для приложения
CREATE USER IF NOT EXISTS 'bi_bot_user'@'%' IDENTIFIED BY '${MYSQL_PASSWORD}';
GRANT ALL PRIVILEGES ON partner_db.* TO 'bi_bot_user'@'%';
FLUSH PRIVILEGES;

-- Оптимизация таблиц
OPTIMIZE TABLE partners;
OPTIMIZE TABLE turnovers;

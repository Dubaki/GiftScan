-- ОБНОВЛЕННАЯ СХЕМА ДЛЯ MVP 1:1

TABLE users (
    tg_id BIGINT PRIMARY KEY,
    username VARCHAR(100),
    wallet_address VARCHAR(100),
    subscription_level ENUM('free', 'pro', 'premium') DEFAULT 'free',
    sub_expiry_date TIMESTAMP
);

TABLE gifts_catalog (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100), 
    slug VARCHAR(100) UNIQUE, -- Уникальный идентификатор подарка
    image_url VARCHAR(255),
    total_supply INT
);

TABLE market_snapshots (
    id SERIAL PRIMARY KEY,
    gift_slug VARCHAR(100) REFERENCES gifts_catalog(slug),
    source VARCHAR(50), -- 'Fragment', 'GetGems', 'Portals', 'MRKT'
    price_amount DECIMAL,
    currency VARCHAR(10), -- 'TON', 'USDT'
    scanned_at TIMESTAMP DEFAULT NOW()
);

TABLE deals (
    deal_id UUID PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20), -- 'created', 'waiting_deposit', 'processing', 'completed', 'cancelled'
    
    -- Сторона А (Инициатор)
    initiator_tg_id BIGINT REFERENCES users(tg_id),
    initiator_offer_type VARCHAR(10), -- 'NFT' (в MVP инициатор всегда дает NFT)
    initiator_offer_slug VARCHAR(100), -- slug подарка, который отдает инициатор
    initiator_wallet VARCHAR(100),
    
    -- Сторона Б (Что мы хотим получить взамен)
    required_asset_type VARCHAR(10), -- 'NFT', 'TON', 'JETTON'
    required_asset_slug VARCHAR(100) NULL, -- Если меняем на другой подарок
    required_token_contract VARCHAR(100) NULL, -- Если меняем на USDT/Tonnel (адрес контракта)
    required_amount DECIMAL NULL, -- Сумма (если продажа за деньги)
    
    -- Технические данные для трекинга
    service_wallet_address VARCHAR(100), -- Кошелек гаранта
    deposit_memo_code VARCHAR(50) UNIQUE, -- Уникальный комментарий для отслеживания входящей транзакции
    
    -- Флаги состояния депозитов
    is_initiator_deposited BOOLEAN DEFAULT FALSE,
    is_counterparty_deposited BOOLEAN DEFAULT FALSE
);
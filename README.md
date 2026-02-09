# 🎁 GiftScan - TON NFT Gift Arbitrage Scanner

Автоматический сканер арбитражных возможностей для NFT подарков в сети TON.

## 🚀 Быстрый старт

### 1. Запуск инфраструктуры

```bash
docker-compose up -d
```

### 2. Настройка Telegram бота

```bash
# Получите chat_id от @userinfobot в Telegram
# Добавьте в backend/.env:
TELEGRAM_CHAT_ID=ваш_chat_id
```

### 3. Инициализация БД

```bash
cd backend
python -m alembic upgrade head
```

### 4. Запуск сервера

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 📊 Как это работает

**Каждые 30 секунд:**
1. **TonAPI** собирает цены со всех площадок (GetGems, Portals, MRKT)
2. **Fragment** предоставляет эталонные цены
3. **Orchestrator** сравнивает и находит арбитраж
4. **Telegram** отправляет уведомления при профите > 2 TON

## 🏗️ Архитектура

```
TonAPI Enhanced Parser  →  Arbitrage Orchestrator  →  Telegram Notifier
Fragment Parser         ↗
```

### Активные компоненты

**Парсеры:**
- `tonapi_enhanced.py` - PRIMARY источник (все маркетплейсы)
- `fragment.py` - BENCHMARK (эталонные цены)

**Сервисы:**
- `arbitrage_orchestrator.py` - анализ возможностей
- `telegram_notifier.py` - уведомления
- `continuous_scanner.py` - фоновое сканирование

## ⚙️ Конфигурация

Основные параметры в `backend/.env`:

```bash
# Минимальный профит для уведомлений
MIN_PROFIT_TON=2.0

# Интервал сканирования (секунды)
SCAN_INTERVAL_SEC=30

# Telegram
BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# TonAPI
TONAPI_KEY=your_tonapi_key
```

## 🔍 API Endpoints

- `GET /health` - статус системы
- `GET /api/v1/gifts` - список подарков с ценами
- `GET /api/v1/gifts/{slug}` - детали подарка

## 📈 Пример уведомления

```
🚨 АРБИТРАЖ! 🚨
🏷 Тип: Milk Coffee #1234
💰 Цена покупки: 100.50 TON (GetGems)
📈 Цена на Fragment: 150.00 TON
💸 Чистый профит: 37.30 TON
🔗 https://getgems.io/nft/...
```

## 🛠️ Tech Stack

- **Backend:** FastAPI, SQLAlchemy, asyncpg, aiohttp
- **Database:** PostgreSQL 16, Redis 7
- **Blockchain:** TonAPI (unified marketplace data)
- **Notifications:** Telegram Bot API

## 📝 Документация

- `START_TONAPI.md` - детальный quick start guide
- `123.md` - текущие требования

---

**Статус:** ✅ Production Ready (TonAPI-first architecture)

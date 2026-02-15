# 🎁 GiftScan - TON NFT Gift Arbitrage Scanner

Автоматический сканер арбитражных возможностей для NFT подарков в сети TON с Telegram Mini App интерфейсом.

## 🚀 Быстрый старт

### Автоматический запуск (Windows):

```bash
# Запустить всё одной командой
start_dev.bat
```

### Ручной запуск:

#### 1. Запуск инфраструктуры

```bash
docker-compose up -d
```

#### 2. Инициализация БД (только первый раз)

```bash
cd backend
python -m alembic upgrade head
```

#### 3. Запуск Backend

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 4. Запуск Frontend

```bash
cd frontend
npm install  # только первый раз
npm run dev
```

### 5. Настройка Telegram Mini App

См. подробную инструкцию: **[TELEGRAM_SETUP.md](TELEGRAM_SETUP.md)**

Быстрая версия:
1. Создайте бота через [@BotFather](https://t.me/BotFather)
2. Создайте Mini App через `/newapp`
3. Для разработки используйте ngrok: `ngrok http 5173`
4. Укажите ngrok URL в настройках Mini App

## 📊 Как это работает

### Backend (Автоматический сканер):
**Каждые 30 секунд:**
1. **TonAPI Enhanced** собирает цены со всех площадок (GetGems, MRKT)
2. **Fragment** предоставляет эталонные floor prices
3. **Portals & Tonnel** - прямое API для детальных данных
4. **Orchestrator** сравнивает и находит арбитраж
5. **Telegram** отправляет уведомления при профите > 2 TON
6. **Valuation Service** оценивает редкость (серийные номера, атрибуты)

### Frontend (Telegram Mini App):
1. Пользователь открывает бот в Telegram
2. Видит список всех подарков с актуальными ценами
3. Нажимает на подарок → видит детали и цены со всех площадок
4. Может искать, сортировать и фильтровать подарки
5. Видит арбитражные возможности с спредом

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                     Telegram Mini App                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Gift List    │  │ Gift Details │  │ Search/Filter│      │
│  │ Page         │→ │ Modal        │  │ Sorting      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API
┌────────────────────────▼────────────────────────────────────┐
│                     FastAPI Backend                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ /api/v1/gifts - Multi-marketplace price aggregation │   │
│  │ /api/v1/gifts/{slug} - Gift details with all prices │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Scanner      │→ │ Orchestrator │→ │ Notifier     │     │
│  │ Service      │  │ (Arbitrage)  │  │ (Telegram)   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│         ↓                                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │        5 Marketplace Parsers (Direct APIs)           │   │
│  │ Fragment │ GetGems │ MRKT │ Portals │ Tonnel        │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│           PostgreSQL 16 + Redis 7 (Docker)                  │
└─────────────────────────────────────────────────────────────┘
```

### Активные компоненты

**Frontend (React + Telegram SDK):**
- `DashboardPage.jsx` - главный экран со списком подарков
- `GiftCard.jsx` - карточка подарка с ценами
- `GiftDetailModal.jsx` - детальная информация
- `FilterBar.jsx` - поиск и фильтры

**Backend Парсеры:**
- `tonapi_enhanced.py` - GetGems + MRKT через TonAPI
- `fragment.py` - Fragment (официальный маркетплейс)
- `portals_direct.py` - Portals через прямое API
- `tonnel_direct.py` - Tonnel через прямое API

**Backend Сервисы:**
- `scanner.py` - оркестрация сканирования
- `arbitrage_orchestrator.py` - анализ возможностей
- `valuation.py` - оценка редкости NFT
- `telegram_notifier.py` - уведомления
- `new_listing_scanner.py` - мониторинг новых листингов

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

### Backend API

- `GET /health` - статус системы
- `GET /api/v1/gifts` - список подарков с ценами
  - Query params: `sort_by`, `sort_order`, `min_spread_pct`, `search`
  - Поддержка кэширования в Redis
- `GET /api/v1/gifts/{slug}` - детали подарка со всех площадок
- `GET /docs` - Swagger документация

### Frontend Routes

- `/` - главная страница (список подарков)
- `/escrow` - P2P сделки (в разработке)
- `/profile` - профиль пользователя (в разработке)

## 📱 Интерфейс Telegram Mini App

### Главный экран
```
┌──────────────────────────────────────┐
│  🎁 Scanner                    3 arb │
│  ──────────────────────────────────  │
│  5 sources · 35 gifts · 2m ago       │
│                                       │
│  🔍 [Search gifts...]                │
│                                       │
│  ┌────────────────────────────────┐  │
│  │ 🎁 Astral Shard         +25%  │  │
│  │ Frag:250 GG:200 Ton:250       │  │
│  │ 200.00 TON  ← GetGems         │  │
│  └────────────────────────────────┘  │
│                                       │
│  ┌────────────────────────────────┐  │
│  │ 💍 Bling Binky        +351%   │  │
│  │ Frag:33 GG:35 MR:149 Ton:58   │  │
│  │ 33.00 TON  ← Fragment         │  │
│  └────────────────────────────────┘  │
│  ...                                  │
└──────────────────────────────────────┘
```

### Детали подарка (при клике)
```
┌──────────────────────────────────────┐
│           ────                        │
│                                       │
│  🎁 Astral Shard              +25%   │
│  astralshard · 10,000 supply         │
│                                       │
│  Best price    │  Worst price        │
│  200 TON       │  250 TON            │
│  GetGems       │  Fragment           │
│                                       │
│  Spread: 50.00 TON (25%)             │
│                                       │
│  PRICES BY MARKETPLACE               │
│  ● GetGems     200.00 TON            │
│  ○ Portals     207.39 TON            │
│  ○ Fragment    250.00 TON            │
│  ○ Tonnel      250.00 TON            │
│                                       │
│  [ Close ]                            │
└──────────────────────────────────────┘
```

## 📈 Пример уведомления

```
🚨 АРБИТРАЖ! 🚨
🏷 Тип: Milk Coffee #1234
💰 Цена покупки: 100.50 TON (GetGems)
📈 Цена на Fragment: 150.00 TON
💸 Чистый профит: 37.30 TON
🔗 https://getgems.io/nft/...
```

## ✨ Новые возможности

### 🔍 Система оценки редкости
- **Серийные номера**: Премия +20% за номера < 1000
- **Красивые номера**: Премия +15% за #777, #420, #1234, #5555
- **Редкие атрибуты**: Премия +50% за Black Backdrop
- **Комбинированные премии**: До +70% для особо ценных NFT

### 📊 Детальная аналитика
- **Атрибуты NFT**: Model, Backdrop, Symbol сохраняются в JSONB
- **Серийные номера**: Отслеживание для каждого NFT
- **Мониторинг новых листингов**: Автоматическое обнаружение новых продаж
- **Multi-marketplace сравнение**: 5 площадок в одном месте

### 💎 Найденные возможности
Реальные примеры из последнего сканирования:
- **Bling Binky**: 33 TON (Fragment) → 149 TON (MRKT) = **116 TON спред!**
- **Loot Bag #229**: Недооценен на 40 TON (премия за низкий номер)
- **Astral Shard**: 200 TON (GetGems) → 250 TON (Fragment) = **50 TON спред**

## 🛠️ Tech Stack

**Backend:**
- FastAPI, SQLAlchemy (async), asyncpg, aiohttp
- PostgreSQL 16 (с JSONB для атрибутов), Redis 7
- TonAPI (unified marketplace data)
- Telegram Bot API для уведомлений

**Frontend:**
- React 19, React Router 7
- Vite 6 (dev server + bundler)
- Tailwind CSS 4
- Telegram Web App SDK (@twa-dev/sdk)
- Responsive design для мобильных устройств

## 📝 Документация

### Для разработки:
- **QUICK_START.md** - быстрый старт за 5 минут
- **TELEGRAM_SETUP.md** - настройка Telegram Mini App
- **TELEGRAM_APP_READY.md** - итоговая инструкция по запуску
- **FEATURES.md** - полный список возможностей
- `START_TONAPI.md` - детальный quick start guide
- `123.md` - текущие требования

### Для деплоя:
- **DEPLOY_QUICK.md** - быстрый деплой на Render.com (5 мин)
- **RENDER_DEPLOY.md** - детальная инструкция по деплою
- **RENDER_CHECKLIST.txt** - чеклист для деплоя
- `render.yaml` - автоматическая конфигурация Blueprint

## 🌐 Production Deployment

### Деплой на Render.com (рекомендуется)

**Быстрый способ (5 минут):**
```bash
# 1. Загрузить код на GitHub
git push origin main

# 2. Render Dashboard → New → Blueprint
# 3. Connect repository
# 4. Apply (автоматически создаст всё из render.yaml)
```

**Что будет создано бесплатно:**
- ✅ Backend API (FastAPI)
- ✅ Frontend (React Static Site)
- ✅ PostgreSQL (бесплатно 90 дней)
- ✅ Redis (бесплатно навсегда)
- ✅ Auto-deploy on git push

**Подробности**: См. **DEPLOY_QUICK.md** или **RENDER_DEPLOY.md**

**Стоимость:**
- Первые 90 дней: **БЕСПЛАТНО**
- После: **$7/мес** (только PostgreSQL)
- Production: **$14/мес** (backend не спит)

---

**Статус:** ✅ Production Ready | 🚀 Deploy Ready (Render.com)

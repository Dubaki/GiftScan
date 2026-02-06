# GiftScan — Прогресс разработки

## Дата начала: 05.02.2026
## Последнее обновление: 06.02.2026

---

## Что сделано

### Инфраструктура
- [x] Склонирован репозиторий, развернута локальная среда разработки
- [x] Поднят Docker-стек: PostgreSQL 16, Redis 7, PgAdmin
- [x] Создан `.env` из шаблона с дефолтными параметрами подключения

### База данных
- [x] Инициализирована Alembic-миграция (4 таблицы: `users`, `gifts_catalog`, `market_snapshots`, `deals`)
- [x] Миграция применена к PostgreSQL
- [x] Засеяно 107 подарков в каталог (`gifts_catalog`)

### Backend (FastAPI)
- [x] Установлены все Python-зависимости
- [x] Сервер запущен на `http://localhost:8000`
- [x] Работает фоновый сканер цен (price_updater, интервал 600с)
- [x] Парсер Fragment.com успешно получает floor-цены подарков
- [x] API эндпоинты доступны:
  - `GET /health` — проверка состояния
  - `GET /api/v1/gifts` — каталог подарков с ценами (мультимаркетплейс)
  - `GET /api/v1/gifts/{slug}` — детали одного подарка
  - `POST /api/v1/deals/create` — создание escrow-сделки
  - `GET /api/v1/deals/{deal_id}` — детали сделки
  - `POST /api/v1/deals/{deal_id}/check-deposit` — проверка депозита (mock)

### Frontend (React + Vite)
- [x] Установлены Node.js-зависимости
- [x] Dev-сервер запущен на `http://localhost:5174`
- [x] Работают страницы: Dashboard (сканер), Profile (профиль Telegram)
- [x] Компоненты: GiftCard, TabBar (нижняя навигация)

---

## Фаза 1 — Мультимаркетплейс сканер (В ПРОЦЕССЕ)

### Архитектура парсеров
- [x] Создан базовый класс `BaseParser` с интерфейсом `fetch_gift_price(slug)` и `fetch_all_prices()`
- [x] Создан `GiftPrice` dataclass для унификации результатов парсеров
- [x] Создан реестр парсеров `PARSER_REGISTRY` для динамического подключения

### Парсеры маркетплейсов
- [x] **Fragment** — полностью работает (HTML-скрапинг, 3 стратегии парсинга)
- [ ] **GetGems** — заглушка (API защищён WAF, нужен TonAPI или browser automation)
- [ ] **Tonnel** — заглушка (требует Telegram initData auth)
- [ ] **MRKT** — заглушка (требует Telegram initData auth)
- [ ] **Portals** — заглушка (требует Telegram initData auth)

### Сканер
- [x] Рефакторинг `scanner.py` для работы с `PARSER_REGISTRY`
- [x] Параллельное сканирование с семафорами (per-source + global)
- [x] Поддержка bulk-парсеров (один запрос на все подарки)
- [x] Логирование статистики сканирования по источникам

### API
- [x] Обновлена схема `GiftOut` — массив `prices` со всех площадок
- [x] Добавлены поля `best_price`, `worst_price`, `spread_ton`, `spread_pct`, `arbitrage_signal`
- [x] Сортировка по `name`, `best_price`, `spread_pct`
- [x] Фильтрация по `min_spread_pct` и `search`
- [x] Добавлен эндпоинт `GET /api/v1/gifts/{slug}` для детальной информации

### Redis-кеширование
- [x] Создан сервис `CacheService` с поддержкой Redis
- [x] Кеширование полного ответа API (TTL 15 мин)
- [x] Инвалидация кеша после каждого сканирования

### Frontend
- [x] Обновлён `client.js` — поддержка query-параметров сортировки/фильтрации
- [x] Создан компонент `SpreadBadge` — цветовой бейдж спреда (зелёный/жёлтый/серый)
- [x] Создан компонент `FilterBar` — сортировка и фильтрация
- [x] Обновлён `GiftCard` — отображение мультимаркетплейс цен, лучшая цена, мини-список
- [x] Обновлён `DashboardPage` — фильтры, счётчик арбитражных сигналов, время сканирования

---

## Следующие шаги

### Фаза 1 (осталось)
- [ ] Подключить GetGems через TonAPI или browser automation
- [ ] Получить auth-токены для Tonnel/MRKT/Portals
- [ ] Добавить детальную страницу/модалку подарка с графиком цен
- [ ] Интегрировать Redis-кеш в API-эндпоинт (cache-first)

### Фаза 2 — Escrow (Гарант-сделки)

#### TON блокчейн интеграция
- [ ] Подключить TON SDK (Tonweb / Pytonlib)
- [ ] Реализовать проверку входящих транзакций по memo-коду
- [ ] Проверка владения NFT-подарком
- [ ] Отправка подарков и крипты по завершении сделки
- [ ] Поддержка Native TON, USDT (Jetton), Tonnel

#### Frontend escrow
- [ ] Форма создания сделки (выбор подарка, тип сделки, цена)
- [ ] Страница деталей сделки (статус, таймер, QR для оплаты)
- [ ] Верификация депозита в UI
- [ ] Страница "Мои сделки" с историей

### Фаза 3 — Telegram-бот
- [ ] Создать Telegram-бота для уведомлений о сделках
- [ ] Команды бота: создание сделки, проверка статуса, отмена
- [ ] Валидация `initData` от Telegram WebApp на бэкенде
- [ ] Deep-link интеграция (открытие Mini App из бота)

### Фаза 4 — Продакшн
- [ ] Dockerfile для backend и frontend
- [ ] CI/CD пайплайн (GitHub Actions)
- [ ] Настройка HTTPS, домен
- [ ] Мониторинг и логирование (Sentry, Grafana)
- [ ] Rate limiting и защита API
- [ ] Подписочная модель (free / pro / premium)

---

## Текущие сервисы

| Сервис | Адрес | Порт |
|--------|-------|------|
| Backend (FastAPI) | http://localhost:8000 | 8000 |
| Frontend (Vite) | http://localhost:5174 | 5174 |
| PostgreSQL | localhost | 5432 |
| Redis | localhost | 6379 |
| PgAdmin | http://localhost:5050 | 5050 |

## Доступы по умолчанию

| Сервис | Логин | Пароль |
|--------|-------|--------|
| PostgreSQL | giftscan | giftscan_secret |
| PgAdmin | admin@giftscan.local | admin |

---

## Структура файлов (обновлено)

### Backend
```
backend/
├── app/
│   ├── api/routes/
│   │   ├── deals.py
│   │   └── gifts.py          # Обновлён — мультимаркетплейс API
│   ├── core/
│   │   ├── config.py
│   │   └── database.py
│   ├── models/
│   │   ├── deal.py
│   │   ├── gift.py
│   │   ├── snapshot.py
│   │   └── user.py
│   ├── schemas/
│   │   ├── deal.py
│   │   └── gift.py           # Обновлён — новая схема с prices[]
│   ├── services/
│   │   ├── cache.py          # Новый — Redis-кеширование
│   │   ├── escrow.py
│   │   ├── scanner.py        # Обновлён — мультипарсер
│   │   └── parsers/
│   │       ├── __init__.py   # Новый — реестр парсеров
│   │       ├── base.py       # Новый — базовый класс
│   │       ├── fragment.py   # Обновлён — класс FragmentParser
│   │       ├── getgems.py    # Новый — заглушка
│   │       ├── mrkt.py       # Новый — заглушка
│   │       ├── portals.py    # Новый — заглушка
│   │       └── tonnel.py     # Новый — заглушка
│   ├── workers/
│   │   └── price_updater.py  # Обновлён — инвалидация кеша
│   ├── main.py
│   └── seeds.py
└── requirements.txt
```

### Frontend
```
frontend/
├── src/
│   ├── api/
│   │   └── client.js         # Обновлён — query-параметры
│   ├── components/
│   │   ├── FilterBar.jsx     # Новый — фильтры и сортировка
│   │   ├── GiftCard.jsx      # Обновлён — мультимаркетплейс
│   │   ├── SpreadBadge.jsx   # Новый — бейдж спреда
│   │   └── TabBar.jsx
│   ├── pages/
│   │   ├── DashboardPage.jsx # Обновлён — фильтры, статистика
│   │   ├── EscrowPage.jsx
│   │   └── ProfilePage.jsx
│   └── ...
└── package.json
```

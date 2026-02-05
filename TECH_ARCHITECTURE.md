# Technical Architecture

## Стек технологий
- **Frontend:** React + Vite + TailwindCSS (Telegram WebApp).
- **Backend:** Python (FastAPI).
- **Blockchain:** TON SDK (Tonweb / Pytonlib) для проверки владения подарками и мониторинга транзакций.
- **Database:** PostgreSQL (хранение пользователей и истории сделок) + Redis (кеширование текущих цен для быстрого доступа).

## Источники данных (Data Sources)
ИИ должен написать парсеры или API-клиенты для:
1. **Fragment:** Парсинг HTML или API для получения Floor Price подарков.
2. **GetGems:** API для получения текущих листингов.
3. **Portals**
4. **Tonnel (Tonnel Relayer)**
5. **MRKT**


## Логика обновлений
- Использовать Background Tasks (Celery/Arq) для обновления цен каждые N секунд.
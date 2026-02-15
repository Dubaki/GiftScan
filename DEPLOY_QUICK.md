# ⚡ Quick Deploy на Render.com (5 минут)

## 🎯 Быстрая инструкция

### 1. Подготовка (1 мин)
```bash
# Создать Git репозиторий (если еще нет)
git init
git add .
git commit -m "Ready for Render deployment"

# Загрузить на GitHub
# Создайте новый репозиторий на github.com
git remote add origin https://github.com/ваш-username/giftscan.git
git push -u origin main
```

### 2. Render Dashboard (2 мин)
1. Открыть https://dashboard.render.com
2. Click **"New"** → **"Blueprint"**
3. Connect GitHub repository
4. Render найдет `render.yaml` автоматически
5. Click **"Apply"**

### 3. Environment Variables (1 мин)
После создания сервисов, добавить в `giftscan-api`:

```
TELEGRAM_BOT_TOKEN = получить от @BotFather
TELEGRAM_CHAT_ID = получить от @userinfobot
```

Опционально (для полного функционала):
```
TONAPI_KEY = получить на tonapi.io
PORTALS_AUTH_TOKEN = получить в Portals
```

### 4. Обновить Telegram Bot (1 мин)
```
@BotFather → /myapps → Edit Web App URL
Вставить: https://giftscan-frontend.onrender.com
```

### 5. Проверка (30 сек)
```bash
# Backend
curl https://giftscan-api.onrender.com/health

# Frontend в браузере
https://giftscan-frontend.onrender.com

# Telegram
https://t.me/ваш_бот/giftscan
```

---

## ✅ Что будет создано

Render автоматически создаст:

1. **PostgreSQL** (Free для первых 90 дней)
   - URL: `giftscan-db.internal`
   - 256MB RAM, 1GB storage

2. **Redis** (Free навсегда)
   - URL: `giftscan-redis.internal`
   - 25MB storage

3. **Backend API** (Free, спит после 15 мин)
   - URL: `https://giftscan-api.onrender.com`
   - Python 3.11, FastAPI
   - Auto-deploy on git push

4. **Frontend** (Free навсегда)
   - URL: `https://giftscan-frontend.onrender.com`
   - React + Vite static site
   - Auto-deploy on git push

---

## 💰 Стоимость

**Первые 90 дней: БЕСПЛАТНО!**

После:
- PostgreSQL: $7/мес (или удалить и использовать другую БД)
- Всё остальное: БЕСПЛАТНО

Для production (опционально):
- Paid Backend (не спит): +$7/мес
- **Total: $14/мес** для полноценного приложения

---

## 🔄 Обновления

После настройки:
```bash
git add .
git commit -m "Update"
git push

# Render автоматически задеплоит за 2-3 минуты!
```

---

## 🐛 Проблемы?

### Backend не стартует
```bash
# Проверить логи: Render Dashboard → giftscan-api → Logs
# Чаще всего нужно добавить TELEGRAM_BOT_TOKEN
```

### Frontend не загружает данные
```bash
# Проверить VITE_API_URL в frontend environment variables
# Должно быть: https://giftscan-api.onrender.com/api/v1
```

### Бесплатный plan засыпает
```bash
# Настроить UptimeRobot (бесплатно):
# 1. Создать аккаунт на uptimerobot.com
# 2. Add Monitor → HTTP(s)
# 3. URL: https://giftscan-api.onrender.com/health
# 4. Interval: Every 10 minutes
# Это будет "будить" backend автоматически
```

---

## 📖 Подробная инструкция

См. **RENDER_DEPLOY.md** для детальных инструкций.

---

**Итого: ~5 минут до production deployment!** 🚀

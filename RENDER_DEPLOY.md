# 🚀 Деплой GiftScan на Render.com

## 📋 Подготовка

### Шаг 1: Создать аккаунт на Render
1. Перейти на https://render.com
2. Зарегистрироваться (можно через GitHub)
3. Подтвердить email

### Шаг 2: Подготовить репозиторий
```bash
# Если еще нет Git репозитория
git init
git add .
git commit -m "Initial commit for Render deployment"

# Создать репозиторий на GitHub
# Затем:
git remote add origin https://github.com/ваш-username/giftscan.git
git branch -M main
git push -u origin main
```

---

## 🏗️ Деплой через Blueprint (рекомендуется)

### Вариант A: Автоматический деплой через render.yaml

1. **Перейти в Render Dashboard**
   - https://dashboard.render.com/

2. **Создать новый Blueprint**
   - Click: "New" → "Blueprint"
   - Connect your GitHub repository
   - Render автоматически найдет `render.yaml`

3. **Настроить переменные окружения**

   В Render Dashboard для сервиса `giftscan-api` добавьте:
   ```
   TELEGRAM_BOT_TOKEN=ваш_токен_от_BotFather
   TELEGRAM_CHAT_ID=ваш_chat_id
   TONAPI_KEY=ваш_tonapi_key (опционально)
   PORTALS_AUTH_TOKEN=ваш_portals_token (опционально)
   ```

4. **Deploy**
   - Click "Apply"
   - Render создаст:
     - PostgreSQL database (бесплатно 90 дней)
     - Redis instance (бесплатно, 25MB)
     - Backend API (бесплатно, спит после 15 мин)
     - Frontend static site (бесплатно)

---

## 🔧 Ручной деплой (альтернатива)

Если не хотите использовать Blueprint:

### 1. PostgreSQL Database

1. Dashboard → "New" → "PostgreSQL"
2. Name: `giftscan-db`
3. Database: `giftscan`
4. User: `giftscan`
5. Region: Frankfurt (ближе к Европе)
6. Plan: **Free** (90 дней бесплатно)
7. Create Database
8. **Сохраните Internal Database URL** (понадобится для Backend)

### 2. Redis

1. Dashboard → "New" → "Redis"
2. Name: `giftscan-redis`
3. Region: Frankfurt
4. Plan: **Free** (25MB)
5. Create Redis
6. **Сохраните Internal Redis URL**

### 3. Backend API

1. Dashboard → "New" → "Web Service"
2. Connect your GitHub repository
3. Settings:
   - **Name**: `giftscan-api`
   - **Region**: Frankfurt
   - **Branch**: main
   - **Root Directory**: `backend`
   - **Runtime**: Python 3
   - **Build Command**: `./build.sh`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free

4. **Environment Variables**:
   ```
   DATABASE_URL = [скопировать из PostgreSQL Internal URL]
   REDIS_URL = [скопировать из Redis Internal URL]
   TELEGRAM_BOT_TOKEN = ваш_токен
   TELEGRAM_CHAT_ID = ваш_chat_id
   TONAPI_KEY = ваш_ключ (опционально)
   MIN_PROFIT_TON = 2.0
   SCAN_INTERVAL_SEC = 30
   DEBUG = False
   ```

5. Click "Create Web Service"

### 4. Frontend

1. Dashboard → "New" → "Static Site"
2. Connect your GitHub repository
3. Settings:
   - **Name**: `giftscan-frontend`
   - **Branch**: main
   - **Root Directory**: (оставить пустым)
   - **Build Command**: `cd frontend && npm install && npm run build`
   - **Publish Directory**: `frontend/dist`

4. **Environment Variables**:
   ```
   VITE_API_URL = https://giftscan-api.onrender.com/api/v1
   ```
   (замените `giftscan-api` на имя вашего backend сервиса)

5. Click "Create Static Site"

---

## 🔗 Обновление Telegram Mini App URL

После деплоя frontend получите URL (например: `https://giftscan-frontend.onrender.com`)

### Обновить в @BotFather:

```
/myapps
Выбрать ваше приложение
Edit → Web App URL
Вставить: https://giftscan-frontend.onrender.com
```

---

## ✅ Проверка работоспособности

### 1. Backend Health Check
```bash
curl https://giftscan-api.onrender.com/health
```

Должен вернуть:
```json
{"status":"ok","db":"connected"}
```

### 2. API Test
```bash
curl https://giftscan-api.onrender.com/api/v1/gifts?limit=1
```

### 3. Frontend
Откройте в браузере:
```
https://giftscan-frontend.onrender.com
```

### 4. Telegram Mini App
```
https://t.me/ваш_бот/giftscan
```

---

## 📊 Мониторинг

### Логи Backend
1. Render Dashboard → `giftscan-api`
2. Tab: "Logs"
3. Real-time логи всех запросов

### Логи Frontend
1. Render Dashboard → `giftscan-frontend`
2. Tab: "Logs"
3. Логи сборки и деплоя

### Database
1. Render Dashboard → `giftscan-db`
2. Tab: "Metrics"
3. Disk usage, connections, queries

---

## 🐛 Troubleshooting

### Backend не запускается

**Проблема**: "Build failed"
```bash
# Проверьте логи сборки
# Чаще всего проблема в:
# 1. Отсутствие build.sh или неправильные права
# 2. Ошибки в requirements.txt
```

**Решение**:
```bash
# Локально протестируйте build.sh
cd backend
bash build.sh
```

### Миграции не применились

**Проблема**: Таблиц нет в БД

**Решение**:
```bash
# В Render Console (для сервиса giftscan-api):
# Shell → Connect
alembic upgrade head
```

### Frontend не грузит данные

**Проблема**: CORS ошибки или 404

**Решение**:
1. Проверьте `VITE_API_URL` в frontend env vars
2. URL должен быть: `https://giftscan-api.onrender.com/api/v1` (без слэша в конце)
3. Backend CORS уже настроен на `allow_origins=["*"]`

### Бесплатный plan "засыпает"

**Проблема**: Backend спит после 15 минут неактивности

**Решение 1** - Ping сервис (бесплатный workaround):
```bash
# Использовать UptimeRobot или Cron-job.org
# Ping каждые 10 минут: https://giftscan-api.onrender.com/health
```

**Решение 2** - Upgrade to Paid Plan ($7/месяц):
- Никогда не спит
- Faster builds
- Больше ресурсов

---

## 💰 Стоимость

### Бесплатный tier (достаточно для MVP):
- ✅ PostgreSQL: Бесплатно 90 дней, потом $7/мес
- ✅ Redis: Бесплатно навсегда (25MB)
- ✅ Backend Web Service: Бесплатно (спит после 15 мин)
- ✅ Frontend Static Site: Бесплатно навсегда

**Total: $0/месяц** (первые 90 дней)
**После 90 дней: $7/месяц** (только PostgreSQL)

### Платный план (для production):
- PostgreSQL: $7/мес
- Redis: $7/мес (или бесплатный 25MB)
- Backend: $7/мес (не спит, больше ресурсов)
- Frontend: Бесплатно

**Total: $14-21/месяц**

---

## 🔄 Автоматические обновления

После настройки каждый `git push` в main ветку автоматически:
1. Пересобирает backend (если изменился)
2. Пересобирает frontend (если изменился)
3. Применяет миграции
4. Перезапускает сервисы

```bash
# Обновить код
git add .
git commit -m "Update features"
git push origin main

# Render автоматически задеплоит за 2-3 минуты
```

---

## 📝 Чеклист деплоя

- [ ] Создан аккаунт на Render.com
- [ ] Код загружен на GitHub
- [ ] PostgreSQL создан
- [ ] Redis создан
- [ ] Backend API задеплоен
- [ ] Environment variables настроены
- [ ] Frontend задеплоен
- [ ] Telegram Bot URL обновлен в @BotFather
- [ ] Проверен /health endpoint
- [ ] Проверена загрузка данных в Telegram
- [ ] Настроен UptimeRobot (опционально)

---

## 🎉 Готово!

Ваш GiftScan MVP теперь доступен 24/7 на:
- Backend: https://giftscan-api.onrender.com
- Frontend: https://giftscan-frontend.onrender.com
- Telegram: https://t.me/ваш_бот/giftscan

**Время деплоя: ~15-20 минут**

---

## 🔗 Полезные ссылки

- [Render Docs](https://render.com/docs)
- [Render Blueprint Spec](https://render.com/docs/blueprint-spec)
- [Free Tier Limits](https://render.com/docs/free)
- [PostgreSQL Backup](https://render.com/docs/postgresql-backups)

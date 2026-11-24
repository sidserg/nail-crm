# Nail CRM — страница «Обзор»

Скопируйте файлы из архива в корень проекта с сохранением путей.

## Новые файлы
- backend/app/routers/overview.py
- frontend/src/pages/OverviewPage.jsx

## Изменённые файлы
- backend/app/main.py — подключён роутер overview
- frontend/src/App.jsx — пункт меню и маршрут /overview
- frontend/src/pages/CalendarPage.jsx — поддержка ?date=YYYY-MM-DD
- frontend/src/styles.css — стили тепловой карты

## Запуск
Backend: перезапустите FastAPI. Миграции БД не нужны.
Frontend: npm run build (или npm run dev для разработки).

## Проверка
GET /api/overview/stats?year=2026&month=12
Требуется Bearer-токен, как и для остальных приватных API.

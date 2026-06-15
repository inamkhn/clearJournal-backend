# ClearJournal API

A **crypto trading journal** backend built with FastAPI. Helps traders track, analyze, and showcase their trading performance across multiple exchanges.

## Features

- **Trade Management** — Import and manage trades from crypto exchanges (Binance, Bybit, etc.) with full execution history
- **Analytics** — Trade statistics, progress tracking, cross-analysis, kline data, and ClearJournal scoring
- **Trading Journal** — Attach notes and chart screenshots (S3-backed) to individual trades
- **Wallet Tracking** — Monitor wallet balances and fiat exposure across accounts
- **Verification Pages** — Public-facing pages where traders can showcase verified performance
- **Billing & Subscriptions** — Subscription plans with Tap Payments integration, invoicing, and admin panel
- **AI Conversations** — Chat with an AI assistant about your trading (Anthropic-powered)
- **Exchange Sync** — Background Celery workers sync trades and balances from connected exchanges

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI + Uvicorn |
| ORM | SQLModel (SQLAlchemy) |
| Database | PostgreSQL 16 |
| Cache/Queue | Redis + Celery |
| Migrations | Alembic |
| Storage | AWS S3 (boto3) |
| Payments | Tap Payments |
| AI | Anthropic |
| Email | SendGrid |

## Quick Start

### 1. Clone & Install

```bash
git clone <repo-url>
cd clearJournal
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Fill in your credentials in .env
```

### 3. Run Migrations

```bash
alembic upgrade head
```

### 4. Start the Server

```bash
uvicorn main:app --reload --port 8000
```

API docs available at **http://localhost:8000/docs**

## Docker

```bash
docker-compose up --build
```

Starts the API, Celery worker, PostgreSQL, and Redis.

## Project Structure

```
app/
├── api/v1/          # Route handlers (endpoints)
├── core/            # Config, security, middleware, S3, Redis, Celery
├── crud/            # Base CRUD operations
├── db/              # Database session
├── models/          # SQLModel ORM models
├── schemas/         # Pydantic request/response schemas
├── services/        # Business logic layer
└── utils/           # Pagination, date/math/symbol helpers
alembic/versions/    # Database migrations
tests/               # Test suite
```

## API Endpoints

| Module | Prefix | Description |
|--------|--------|-------------|
| Auth | `/api/v1/auth` | Registration, login, password reset |
| Trades | `/api/v1/trades` | Trade CRUD with filtering & statistics |
| Notes | `/api/v1/notes` | Journal notes with image attachments |
| Exchanges | `/api/v1/exchanges` | Supported exchange list |
| Exchange Accounts | `/api/v1/exchange-accounts` | Connected exchange accounts |
| Wallets | `/api/v1/wallets` | Wallet tracking |
| Billing | `/api/v1/billing` | Checkout, subscriptions, invoices |
| Products/Prices | `/api/v1/products`, `/api/v1/prices` | Subscription plans |
| Verification Pages | `/api/v1/verification-pages` | Public performance pages |
| Conversations | `/api/v1/conversations` | AI chat |
| Admin | `/api/v1/admin` | Subscription management (admin) |

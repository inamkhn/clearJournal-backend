from fastapi import APIRouter
from app.api.v1 import (
    auth, admin, exchanges, exchange_accounts,
    wallet_accounts, wallets, trades, trade_executions,
    trade_tags, tags, notes, note_images, storages,
    fiat_exposure, progress, cross_analysis,
    clearjournal_score, verification_pages,
    conversations, messages, user_instructions,
    billing, products, prices, coin_price_history,
    emails, reviews, contact_us, feedback, health
)

api_router = APIRouter()

api_router.include_router(auth.router,                prefix="/auth",                    tags=["authentication"])
api_router.include_router(admin.router,               prefix="/admin",                   tags=["admin"])
api_router.include_router(exchanges.router,           prefix="/exchanges",               tags=["exchanges"])
api_router.include_router(exchange_accounts.router,   prefix="/exchange-accounts",       tags=["exchange_accounts"])
api_router.include_router(wallet_accounts.router,     prefix="/wallet-accounts",         tags=["wallet_accounts"])
api_router.include_router(wallets.router,             prefix="/wallets",                 tags=["wallets"])
api_router.include_router(trades.router,              prefix="/trades",                  tags=["trades"])
api_router.include_router(trade_executions.router,    prefix="/trade-executions",        tags=["trade-executions"])
api_router.include_router(trade_tags.router,          prefix="/trade-tags",              tags=["trade-tags"])
api_router.include_router(tags.router,                prefix="/tags",                    tags=["tags"])
api_router.include_router(notes.router,               prefix="/notes",                   tags=["notes"])
api_router.include_router(note_images.router,         prefix="/note-images",             tags=["note_images"])
api_router.include_router(storages.router,            prefix="/storages",                tags=["storages"])
api_router.include_router(fiat_exposure.router,       prefix="/fiat_exposure",           tags=["fiat_exposure"])
api_router.include_router(progress.router,            prefix="/progress",                tags=["progress"])
api_router.include_router(cross_analysis.router,      prefix="/cross-analysis",          tags=["cross-analysis"])
api_router.include_router(clearjournal_score.router,  prefix="/clearjournal-score",      tags=["ClearJournal Score"])
api_router.include_router(verification_pages.router,  prefix="/verification-pages",      tags=["verification-pages"])
api_router.include_router(conversations.router,       prefix="/conversations",           tags=["conversations"])
api_router.include_router(messages.router,            prefix="/messages",                tags=["messages"])
api_router.include_router(user_instructions.router,   prefix="/user-instructions",       tags=["user-instructions"])
api_router.include_router(billing.router,             prefix="/billing",                 tags=["billing"])
api_router.include_router(products.router,            prefix="/products",                tags=["products"])
api_router.include_router(prices.router,              prefix="/prices",                  tags=["prices"])
api_router.include_router(coin_price_history.router,  prefix="/coin-price-history",      tags=["coin_price_history"])
api_router.include_router(emails.router,              prefix="/emails",                  tags=["emails"])
api_router.include_router(reviews.router,             prefix="/reviews",                 tags=["reviews"])
api_router.include_router(contact_us.router,          prefix="/contact-us",              tags=["contact_us"])
api_router.include_router(feedback.router,            prefix="/feedback",                tags=["feedback"])
api_router.include_router(health.router,              prefix="",                         tags=["health"])

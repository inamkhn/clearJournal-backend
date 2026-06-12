from fastapi import APIRouter, Depends
from typing import List

from app.models.exchanges import Exchange
from app.services.exchange.exchange_service import ExchangeService

router = APIRouter()


@router.get("/", response_model=List[Exchange])
def get_exchanges(
    exchange_service: ExchangeService = Depends(),
):
    """
    Returns the master list of all active supported exchanges.
    No authentication required.
    """
    return exchange_service.get_active_exchanges()

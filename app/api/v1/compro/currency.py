from fastapi import APIRouter, HTTPException, Query

from app.schemas.currency import (
    CurrencyConvertRequest,
    CurrencyConvertResponse,
    ExchangeRateResponse,
)
from app.services.shared.currency_service import (
    convert_currency,
    get_exchange_rate_info,
)

router = APIRouter(prefix="/currency", tags=["Currency & Exchange Rates"])


@router.get("/rate", response_model=ExchangeRateResponse)
async def get_current_rate():
    """
    Mendapatkan kurs acuan USD ke IDR terkini (dengan cache update maksimal 24 jam / 1 hari).
    """
    try:
        return await get_exchange_rate_info()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Gagal mengambil informasi kurs: {e!s}"
        )


@router.get("/convert", response_model=CurrencyConvertResponse)
async def convert_get(
    amount: float = Query(..., gt=0, description="Nominal yang ingin dikonversi"),
    from_currency: str = Query(
        "USD", description="Mata uang asal: 'USD' atau 'IDR'"
    ),
    to_currency: str = Query(
        "IDR", description="Mata uang tujuan: 'USD' atau 'IDR'"
    ),
):
    """
    Mengonversi nilai antara USD dan IDR via Query Parameter.
    Contoh: `/currency/convert?amount=100&from_currency=USD&to_currency=IDR`
    """
    try:
        return await convert_currency(
            amount=amount, from_currency=from_currency, to_currency=to_currency
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Gagal melakukan konversi mata uang: {e!s}"
        )


@router.post("/convert", response_model=CurrencyConvertResponse)
async def convert_post(body: CurrencyConvertRequest):
    """
    Mengonversi nilai antara USD dan IDR via JSON Request Body.
    """
    try:
        return await convert_currency(
            amount=body.amount,
            from_currency=body.from_currency,
            to_currency=body.to_currency,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Gagal melakukan konversi mata uang: {e!s}"
        )

from pydantic import BaseModel, Field


class ExchangeRateResponse(BaseModel):
    base_currency: str = "USD"
    target_currency: str = "IDR"
    rate: float = Field(..., description="Nilai 1 USD dalam IDR")
    inverse_rate: float = Field(..., description="Nilai 1 IDR dalam USD")
    last_updated: str = Field(..., description="Waktu pembaruan kurs terakhir (ISO UTC)")
    source: str = "open.er-api.com"


class CurrencyConvertRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Nominal yang ingin dikonversi")
    from_currency: str = Field("USD", description="Mata uang asal (USD atau IDR)")
    to_currency: str = Field("IDR", description="Mata uang tujuan (USD atau IDR)")


class CurrencyConvertResponse(BaseModel):
    amount: float
    from_currency: str
    to_currency: str
    rate: float
    result: float
    formatted_result: str
    last_updated: str

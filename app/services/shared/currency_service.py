import time
from datetime import datetime, timezone
import httpx

# In-memory cache untuk nilai tukar USD -> IDR
# TTL: 24 Jam (86.400 detik) sesuai batas toleransi update maksimal 1 hari
CACHE_TTL_SECONDS = 86400

_currency_cache: dict = {
    "rate": 16000.0,
    "last_updated": None,
    "next_update": None,
    "cached_at": 0.0,
}

PRIMARY_API_URL = "https://open.er-api.com/v6/latest/USD"
FALLBACK_API_URL = "https://api.exchangerate-api.com/v4/latest/USD"


async def fetch_exchange_rate_from_network() -> float | None:
    """Mengambil kurs terbaru dari open exchange rate API."""
    async with httpx.AsyncClient(timeout=8.0) as client:
        # Coba endpoint utama
        try:
            resp = await client.get(PRIMARY_API_URL)
            if resp.status_code == 200:
                data = resp.json()
                idr_rate = data.get("rates", {}).get("IDR")
                if idr_rate and float(idr_rate) > 0:
                    return float(idr_rate)
        except Exception:
            pass

        # Coba fallback endpoint jika yang utama gagal
        try:
            resp = await client.get(FALLBACK_API_URL)
            if resp.status_code == 200:
                data = resp.json()
                idr_rate = data.get("rates", {}).get("IDR")
                if idr_rate and float(idr_rate) > 0:
                    return float(idr_rate)
        except Exception:
            pass

    return None


async def get_exchange_rate_info() -> dict:
    """
    Mendapatkan kurs USD -> IDR terkini.
    Menggunakan cache jika usia data masih di bawah 24 jam (1 hari).
    """
    now = time.time()
    cached_age = now - _currency_cache["cached_at"]

    if cached_age > CACHE_TTL_SECONDS or _currency_cache["last_updated"] is None:
        fresh_rate = await fetch_exchange_rate_from_network()
        if fresh_rate:
            now_iso = datetime.now(timezone.utc).isoformat()
            _currency_cache["rate"] = fresh_rate
            _currency_cache["last_updated"] = now_iso
            _currency_cache["cached_at"] = now

    rate = _currency_cache["rate"]
    last_updated = _currency_cache["last_updated"] or datetime.now(timezone.utc).isoformat()

    return {
        "base_currency": "USD",
        "target_currency": "IDR",
        "rate": rate,
        "inverse_rate": round(1 / rate, 8) if rate > 0 else 0.0,
        "last_updated": last_updated,
        "source": "open.er-api.com",
    }


async def convert_currency(amount: float, from_currency: str, to_currency: str) -> dict:
    """
    Mengonversi nilai antara USD dan IDR.
    """
    from_curr = from_currency.strip().upper()
    to_curr = to_currency.strip().upper()

    rate_info = await get_exchange_rate_info()
    usd_to_idr = rate_info["rate"]

    if from_curr == to_curr:
        result = amount
        rate_used = 1.0
    elif from_curr == "USD" and to_curr == "IDR":
        result = round(amount * usd_to_idr, 2)
        rate_used = usd_to_idr
    elif from_curr == "IDR" and to_curr == "USD":
        result = round(amount / usd_to_idr, 2) if usd_to_idr > 0 else 0.0
        rate_used = round(1 / usd_to_idr, 8) if usd_to_idr > 0 else 0.0
    else:
        raise ValueError(f"Mata uang '{from_curr}' ke '{to_curr}' tidak didukung. Pilihan: USD, IDR.")

    # Format representasi angka untuk memudahkan frontend
    if to_curr == "IDR":
        formatted = f"Rp {result:,.0f}".replace(",", ".")
    else:
        formatted = f"${result:,.2f}"

    return {
        "amount": amount,
        "from_currency": from_curr,
        "to_currency": to_curr,
        "rate": rate_used,
        "result": result,
        "formatted_result": formatted,
        "last_updated": rate_info["last_updated"],
    }

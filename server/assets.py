"""
Catálogo de activos disponibles para seguir (pares de Binance en USDT).

Es una lista curada de las principales criptomonedas; se puede ampliar. Evitamos
consultar todo Binance (son miles) para que la búsqueda sea rápida y simple.
"""

from __future__ import annotations

# símbolo (Binance) -> nombre para mostrar
ASSETS: dict[str, str] = {
    "BTCUSDT": "Bitcoin",
    "ETHUSDT": "Ethereum",
    "BNBUSDT": "BNB",
    "SOLUSDT": "Solana",
    "XRPUSDT": "XRP",
    "ADAUSDT": "Cardano",
    "DOGEUSDT": "Dogecoin",
    "TRXUSDT": "TRON",
    "AVAXUSDT": "Avalanche",
    "DOTUSDT": "Polkadot",
    "MATICUSDT": "Polygon",
    "LINKUSDT": "Chainlink",
    "LTCUSDT": "Litecoin",
    "ATOMUSDT": "Cosmos",
    "UNIUSDT": "Uniswap",
    "APTUSDT": "Aptos",
    "ARBUSDT": "Arbitrum",
    "OPUSDT": "Optimism",
    "NEARUSDT": "NEAR Protocol",
    "INJUSDT": "Injective",
    "SUIUSDT": "Sui",
    "SEIUSDT": "Sei",
    "TIAUSDT": "Celestia",
    "FILUSDT": "Filecoin",
    "ETCUSDT": "Ethereum Classic",
    "BCHUSDT": "Bitcoin Cash",
    "HBARUSDT": "Hedera",
    "ICPUSDT": "Internet Computer",
    "PEPEUSDT": "Pepe",
    "SHIBUSDT": "Shiba Inu",
}

# Temporalidades soportadas
INTERVALS: dict[str, str] = {
    "1h": "Cada hora",
    "4h": "Cada 4 horas",
    "1d": "Diario",
}


def search(query: str = "", limit: int = 50) -> list[dict[str, str]]:
    """Busca activos por símbolo o nombre."""
    q = (query or "").strip().lower()
    items = [
        {"symbol": symbol, "name": name}
        for symbol, name in ASSETS.items()
        if not q or q in symbol.lower() or q in name.lower()
    ]
    return items[:limit]


def is_valid(symbol: str) -> bool:
    return symbol in ASSETS

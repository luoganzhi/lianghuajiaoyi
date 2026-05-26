def normalize_spot_symbol(symbol: str) -> str:
    """Return an OKX spot instrument id, e.g. BTC-USDT."""
    normalized = symbol.split(':', 1)[0].replace('/', '-')
    return normalized.replace('-SWAP', '')


def normalize_futures_symbol(symbol: str) -> str:
    """Return an OKX perpetual swap instrument id, e.g. BTC-USDT-SWAP."""
    normalized = normalize_spot_symbol(symbol)
    if not normalized.endswith('-SWAP'):
        normalized = f"{normalized}-SWAP"
    return normalized

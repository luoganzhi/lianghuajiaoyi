from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass(frozen=True)
class StrategySignal:
    """Normalized strategy output consumed by trading and backtesting."""

    value: int = 0
    action: str = 'hold'
    side: Optional[str] = None
    reason: str = ''
    confidence: float = 1.0

    @property
    def is_entry(self):
        return self.value in (1, -1)

    @property
    def is_long(self):
        return self.value == 1

    @property
    def is_short(self):
        return self.value == -1


def normalize_signal(raw_signal, reason='legacy_signal', confidence=1.0):
    """Convert legacy 1/-1/0 output into StrategySignal."""
    if isinstance(raw_signal, StrategySignal):
        return raw_signal

    value = int(raw_signal or 0)
    if value > 0:
        return StrategySignal(
            value=1,
            action='entry',
            side='long',
            reason=reason,
            confidence=confidence,
        )
    if value < 0:
        return StrategySignal(
            value=-1,
            action='entry',
            side='short',
            reason=reason,
            confidence=confidence,
        )
    return StrategySignal(value=0, action='hold', reason=reason, confidence=confidence)


def normalize_signal_series(raw_signals, index):
    """Normalize legacy list/Series/DataFrame signals to a DataFrame."""
    if isinstance(raw_signals, pd.DataFrame):
        if 'signal' not in raw_signals.columns:
            raise ValueError("信号 DataFrame 必须包含 signal 列")
        raw_series = raw_signals['signal']
    elif isinstance(raw_signals, pd.Series):
        raw_series = raw_signals
    else:
        raw_series = pd.Series(list(raw_signals), index=index[:len(raw_signals)])

    raw_series = raw_series.reindex(index).fillna(0)
    normalized = [normalize_signal(value) for value in raw_series]
    return pd.DataFrame(
        {
            'signal': [signal.value for signal in normalized],
            'action': [signal.action for signal in normalized],
            'side': [signal.side or '' for signal in normalized],
            'reason': [signal.reason for signal in normalized],
            'confidence': [signal.confidence for signal in normalized],
        },
        index=index,
    )

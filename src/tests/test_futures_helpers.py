from src.trading.futures_helpers import (
    calculate_futures_position_size,
    check_existing_take_profit_orders,
    close_futures_position,
    execute_futures_trade,
    set_take_profit_order,
)


class FakeExchange:
    def __init__(self):
        self.created_order = None
        self.native_order = None
        self.pending_response = {'code': '0', 'data': []}

    def create_order(self, symbol, type, side, amount, price=None, params=None):
        self.created_order = {
            'symbol': symbol,
            'type': type,
            'side': side,
            'amount': amount,
            'price': price,
            'params': params or {},
        }
        return {'id': 'order-1', 'status': 'open', **self.created_order}

    def privatePostTradeOrder(self, params):
        self.native_order = params
        return {'code': '0', 'data': [{'ordId': 'native-1'}]}

    def privateGetTradeOrdersPending(self, params):
        self.pending_params = params
        return self.pending_response


class FakeAccount:
    def __init__(self):
        self.exchange = FakeExchange()
        self.leverage_calls = []
        self.balance = 100.0
        self.position = {}

    def set_leverage(self, symbol, leverage):
        self.leverage_calls.append((symbol, leverage))
        return True

    def get_balance(self, currency):
        return self.balance

    def get_position(self, symbol):
        return self.position


def test_calculate_futures_position_size_uses_fixed_margin_formula():
    assert calculate_futures_position_size(fixed_margin=24, leverage=50) == 1.0


def test_execute_futures_trade_places_swap_order_with_leverage():
    account = FakeAccount()

    order = execute_futures_trade(
        account,
        symbol='BTC-USDT-SWAP',
        side='buy',
        amount=0.5,
        leverage=25,
    )

    assert order['id'] == 'order-1'
    assert account.leverage_calls == [('BTC-USDT', 25)]
    assert account.exchange.created_order['symbol'] == 'BTC-USDT-SWAP'
    assert account.exchange.created_order['side'] == 'buy'
    assert account.exchange.created_order['amount'] == 0.5
    assert account.exchange.created_order['params']['tdMode'] == 'isolated'


def test_set_take_profit_order_uses_reduce_only_close_side():
    account = FakeAccount()

    order = set_take_profit_order(
        account,
        symbol='BTC-USDT-SWAP',
        position_type='long',
        amount=-0.5,
        take_profit_price=65000,
    )

    assert order['id'] == 'native-1'
    assert account.exchange.native_order['side'] == 'sell'
    assert account.exchange.native_order['reduceOnly'] == 'true'
    assert account.exchange.native_order['sz'] == '0.5'


def test_check_existing_take_profit_orders_detects_reduce_only_order():
    account = FakeAccount()
    account.exchange.pending_response = {
        'code': '0',
        'data': [{'ordId': 'tp-1', 'reduceOnly': 'true', 'side': 'sell', 'sz': '0.5'}],
    }

    assert check_existing_take_profit_orders(account, 'BTC-USDT-SWAP') is True


def test_close_futures_position_uses_short_close_direction():
    account = FakeAccount()

    close_futures_position(
        account,
        'BTC-USDT-SWAP',
        {'size': 0.5, 'position_type': 'short'},
    )

    assert account.exchange.created_order['side'] == 'buy'
    assert account.exchange.created_order['amount'] == 0.5
    assert account.exchange.created_order['params']['posSide'] == 'short'


def test_close_futures_position_uses_long_close_direction():
    account = FakeAccount()

    close_futures_position(
        account,
        'BTC-USDT-SWAP',
        {'size': 0.5, 'position_type': 'long'},
    )

    assert account.exchange.created_order['side'] == 'sell'
    assert account.exchange.created_order['amount'] == 0.5
    assert account.exchange.created_order['params']['posSide'] == 'long'

import logging

from src.config.config import CONTRACT_CONFIG


def _is_short_position(position_info):
    position_type = position_info.get('position_type')
    if position_type in ('long', 'short'):
        return position_type == 'short'

    return position_info.get('size', 0) < 0


def execute_futures_trade(account, symbol, side, amount, leverage=10, order_type="market", take_profit_price=None):
    """
    执行合约交易
    
    Args:
        account: 交易账户实例
        symbol: 交易对
        side: 交易方向 ('buy' 或 'sell')
        amount: 合约数量
        leverage: 杠杆倍数
        order_type: 订单类型
    
    Returns:
        dict: 订单结果
    """
    try:
        # 合约交易对格式转换
        # 从 BTC-USDT-SWAP 转换为 BTC-USDT
        if symbol.endswith('-SWAP'):
            symbol_for_trade = symbol.replace('-SWAP', '')
        else:
            symbol_for_trade = symbol
        
        # 设置杠杆
        print(f"🔧 正在设置杠杆: {symbol_for_trade} {leverage}x")
        if not account.set_leverage(symbol_for_trade, leverage):
            print(f"❌ 设置杠杆失败: {symbol_for_trade} {leverage}x")
            return None
        print(f"✅ 设置杠杆成功: {symbol_for_trade} {leverage}x")
        
        # 执行合约订单 - 直接调用ccxt的create_order方法
        # 确保使用正确的合约交易对格式
        if not symbol_for_trade.endswith('-SWAP'):
            symbol_for_trade = f"{symbol_for_trade}-SWAP"
        
        # 检查账户余额
        print(f"🔍 检查账户余额...")
        try:
            balance = account.get_balance('USDT')
            if balance is None:
                print(f"⚠️ 无法获取USDT余额")
                balance = 0
            else:
                print(f"💰 当前USDT余额: {balance:.2f} USDT")
            
            # 检查余额是否足够
            required_balance = CONTRACT_CONFIG['fixed_margin']
            if balance < required_balance:
                print(f"❌ 余额不足! 需要至少 {required_balance} USDT，当前余额: {balance:.2f} USDT")
                print(f"💡 请先充值USDT到账户")
                raise ValueError(f"余额不足: 需要 {required_balance} USDT，当前 {balance:.2f} USDT")
            else:
                print(f"✅ 余额充足: {balance:.2f} USDT >= {required_balance} USDT")
        except Exception as e:
            print(f"⚠️ 余额检查失败: {e}")
            print(f"💡 请确保账户中有足够的USDT余额")
        
        # 使用传入的合约张数
        # 注意：这里的amount已经是合约张数，直接使用
        contract_sheets = amount
        
        print(f"🔧 合约张数: {contract_sheets:.4f} 张")
        
        # 验证合约张数是否合理
        if contract_sheets < 0.01:
            print(f"⚠️ 警告: 合约张数太小，无法开仓!")
            print(f"  建议: 增加保证金或使用更高杠杆")
            raise ValueError(f"合约张数太小: {contract_sheets:.4f} 张，无法开仓")
        
        # 设置订单参数 - 尝试不同的posSide设置方式
        # 方法1: 标准CCXT参数
        order_params = {
            'instType': 'SWAP',  # 永续合约
            'tdMode': 'isolated',   # 逐仓模式
        }
        
        # 方法2: 尝试不同的posSide设置方式
        # 注意：根据错误信息，可能需要调整posSide参数
        
        # 暂时不设置posSide参数，避免Parameter posSide error
        # if side == 'buy':
        #     order_params['posSide'] = 'long'
        # elif side == 'sell':
        #     order_params['posSide'] = 'short'
        
        # 确保side参数正确
        order_params['side'] = side
        
        # 根据OKX官方文档设置CCXT参数
        order_params['instType'] = 'SWAP'  # 合约类型
        order_params['tdMode'] = 'isolated'  # 账户模式：逐仓
        
        # 简化CCXT参数设置，移除szType和szFormat参数
        # 让CCXT自动处理参数格式
        print(f"🔧 CCXT使用简化参数")
        
        print(f"🔧 CCXT订单参数: {order_params}")
        
        # 如果有止盈价格，添加到订单参数中
        if take_profit_price is not None:
            order_params['takeProfit'] = {
                'triggerPrice': take_profit_price,
                'price': take_profit_price,
                'type': 'limit'
            }
            print(f"🎯 设置止盈价格: {take_profit_price:.2f} USDT")
        
        # 尝试使用CCXT的合约交易方法
        try:
            order = account.exchange.create_order(
                symbol=symbol_for_trade,
                type=order_type,
                side=side,
                amount=contract_sheets,  # 使用合约张数
                params=order_params
            )
            print(f"✅ CCXT合约交易成功")
            print(f"🔧 CCXT使用合约张数: {contract_sheets:.4f} 张")
        except Exception as ccxt_error:
            print(f"🔧 CCXT合约交易失败，尝试使用OKX原生API: {ccxt_error}")
            
            # 使用OKX原生API调用
            print(f"🔧 OKX原生API使用合约张数: {contract_sheets:.4f} 张")
            
            # 使用传入的合约数量
            order_params_native = {
                'instId': symbol_for_trade,
                'tdMode': 'isolated',  # 逐仓模式
                'side': side,
                'ordType': order_type,
                'sz': str(contract_sheets)  # 使用传入的合约张数
            }
            
            print(f"🔧 确认开仓数量: {contract_sheets:.4f} 张")
            
            # 暂时不设置posSide参数，避免Parameter posSide error
            # 让API自动处理持仓方向
            print(f"🔧 不设置posSide参数，让API自动处理")
            print(f"🔧 使用计算数量: {contract_sheets:.4f} 张")
            
            # 如果后续需要，可以尝试：
            # 1. 先设置持仓模式为双向持仓
            # 2. 再设置posSide参数
            # 3. 或者使用不同的posSide格式
            
            print(f"🔧 OKX原生API参数: {order_params_native}")
            
            # 调用OKX原生API
            order = account.exchange.privatePostTradeOrder(order_params_native)
            print(f"🔧 OKX原生API响应: {order}")
            
            # 转换响应格式以兼容CCXT
            if order and order.get('code') == '0':
                order = {
                    'id': order.get('data', [{}])[0].get('ordId', 'N/A'),
                    'symbol': symbol_for_trade,
                    'type': order_type,
                    'side': side,
                    'amount': contract_sheets,
                    'status': 'closed' if order_type == 'market' else 'open',
                    'okx_response': order
                }
                print(f"✅ OKX原生API合约交易成功")
            else:
                raise Exception(f"OKX原生API调用失败: {order}")
        
        return order
    except Exception as e:
        logging.error(f"合约交易失败: {e}")
        return None

def check_existing_take_profit_orders(account, symbol):
    """
    检查是否已经存在止盈订单
    
    Args:
        account: 交易账户实例
        symbol: 交易对
    
    Returns:
        bool: 是否存在止盈订单
    """
    try:
        # 合约交易对格式转换
        if symbol.endswith('-SWAP'):
            symbol_for_trade = symbol.replace('-SWAP', '')
        else:
            symbol_for_trade = symbol
        
        # 确保使用正确的合约symbol格式
        if not symbol_for_trade.endswith('-SWAP'):
            symbol_for_trade = f"{symbol_for_trade}-SWAP"
        
        # 查询待成交订单
        params = {
            'instId': symbol_for_trade,
            'state': 'live'  # 查询活跃订单
        }
        
        response = account.exchange.privateGetTradeOrdersPending(params)
        
        if response and response.get('code') == '0':
            orders = response.get('data', [])
            for order in orders:
                # 检查是否是减仓单（止盈/止损）
                if order.get('reduceOnly') == 'true':
                    print(f"🔍 发现现有减仓单: {order.get('ordId')} - {order.get('side')} {order.get('sz')}张 @ {order.get('px')}")
                    return True
            
            print(f"🔍 未发现现有止盈单")
            return False
        else:
            print(f"⚠️ 查询订单失败: {response}")
            return False
            
    except Exception as e:
        print(f"❌ 查询现有订单异常: {e}")
        return False

def set_take_profit_order(account, symbol, position_type, amount, take_profit_price):
    """
    设置止盈订单
    
    Args:
        account: 交易账户实例
        symbol: 交易对
        position_type: 持仓类型 ('long' 或 'short')
        amount: 合约数量
        take_profit_price: 止盈价格
    
    Returns:
        dict: 止盈订单结果
    """
    try:
        # 合约交易对格式转换
        if symbol.endswith('-SWAP'):
            symbol_for_trade = symbol.replace('-SWAP', '')
        else:
            symbol_for_trade = symbol
        
        # 确保使用正确的合约symbol格式
        if not symbol_for_trade.endswith('-SWAP'):
            symbol_for_trade = f"{symbol_for_trade}-SWAP"
        
        # 使用传入的数量的绝对值作为止盈数量（API不接受负数）
        contract_sheets = abs(amount)
        
        print(f"🔧 止盈订单设置:")
        print(f"  交易对: {symbol_for_trade}")
        print(f"  持仓类型: {position_type}")
        print(f"  止盈数量: {contract_sheets} 张")
        print(f"  止盈价格: {take_profit_price:.2f} USDT")
        
        # 根据持仓类型确定止盈方向
        # 做多持仓：止盈是卖出(sell)平仓
        # 做空持仓：止盈是买入(buy)平仓
        if position_type == 'long':  # 做多持仓
            tp_side = 'sell'  # 做多平仓
        elif position_type == 'short':  # 做空持仓
            tp_side = 'buy'   # 做空平仓
        else:
            print(f"❌ 无效的持仓类型: {position_type}")
            return None
        
        print(f"  实际止盈方向: {tp_side}")
        
        # 设置止盈订单参数
        order_params_native = {
            'instId': symbol_for_trade,
            'tdMode': 'isolated',
            'side': tp_side,
            'ordType': 'limit',
            'sz': str(contract_sheets),  # 使用传入的数量
            'px': str(take_profit_price),  # 止盈价格
            'reduceOnly': 'true'  # 确保是减仓单
        }
        
        print(f"🔧 OKX原生API止盈参数: {order_params_native}")
        
        # 调用OKX原生API
        order = account.exchange.privatePostTradeOrder(order_params_native)
        print(f"🔧 OKX原生API止盈响应: {order}")
        
        # 转换响应格式以兼容CCXT
        if order and order.get('code') == '0':
            order = {
                'id': order.get('data', [{}])[0].get('ordId', 'N/A'),
                'symbol': symbol_for_trade,
                'type': 'limit',
                'side': tp_side,
                'amount': contract_sheets,
                'price': take_profit_price,
                'status': 'open',
                'okx_response': order
            }
            print(f"✅ 止盈订单设置成功: {take_profit_price:.2f} USDT")
            return order
        else:
            print(f"❌ 止盈订单设置失败: {order}")
            return None
        
    except Exception as e:
        print(f"❌ 设置止盈订单异常: {e}")
        logging.error(f"设置止盈订单失败: {e}")
        return None

def get_futures_position(account, symbol, strategy=None):
    """
    获取合约持仓信息
    
    Args:
        account: 交易账户实例
        symbol: 交易对
        strategy: 策略实例（可选，用于同步状态）
    
    Returns:
        dict: 持仓信息
    """
    try:
        # 合约交易对格式转换
        # 确保使用完整的合约symbol格式
        if not symbol.endswith('-SWAP'):
            symbol_for_query = f"{symbol}-SWAP"
        else:
            symbol_for_query = symbol
        
        # 获取持仓信息
        position = account.get_position(symbol_for_query)
        
        if position and float(position.get('size', 0)) != 0:
            position_info = {
                'size': float(position['size']),
                'entry_price': float(position['entry_price']),
                'unrealized_pnl': float(position['unrealized_pnl']),
                'margin': float(position.get('margin', CONTRACT_CONFIG['fixed_margin'])),  # 使用配置中的保证金
                'leverage': float(position['leverage']),
                'position_type': position.get('position_type', 'unknown'),
                'posSide': position.get('posSide', '')
            }
            
            # 如果提供了策略实例，同步更新策略状态
            if strategy:
                strategy.current_position = position_info['size']
                strategy.entry_price = position_info['entry_price']
                strategy.position_type = position_info['position_type']
                if strategy.debug_mode:
                    logging.info(f"🔍 同步策略状态: 持仓={position_info['size']}, 价格={position_info['entry_price']}, 类型={position_info['position_type']}")
            
            return position_info
        else:
            # 如果没有持仓，重置策略状态
            if strategy:
                strategy.current_position = 0
                strategy.entry_price = 0
                strategy.position_type = None
                if strategy.debug_mode:
                    logging.info(f"🔍 重置策略状态: 无持仓")
            
            return None
    except Exception as e:
        logging.error(f"获取合约持仓失败: {e}")
        return None

def calculate_futures_position_size(fixed_margin=None, price=0, leverage=None):
    """
    计算合约开仓数量 - 基于保证金计算
    
    Args:
        fixed_margin: 固定保证金金额（从配置获取，默认1 USDT）
        price: 当前价格
        leverage: 杠杆倍数
    
    Returns:
        float: 合约数量（张）
    """
    # 如果没有提供参数，使用配置中的默认值
    if fixed_margin is None:
        fixed_margin = CONTRACT_CONFIG['fixed_margin']
    if leverage is None:
        leverage = CONTRACT_CONFIG['leverage']
    
    # ========================================
    # 🎯 基于保证金的合约张数计算公式
    # ========================================
    # 测试结果：0.01张BTC合约 = 0.24 USDT价值
    # 公式：合约张数 = 保证金 / 0.24 * 0.01
    # 保留小数点后2位
    # ========================================
    
    # 0.01张合约的价值（根据实际测试）
    contract_value_per_sheet = 0.24  # USDT/张
    
    # 计算需要的合约张数
    required_contract_sheets = fixed_margin / contract_value_per_sheet * 0.01
    
    # 保留小数点后2位
    position_size = round(required_contract_sheets, 2)
    
    return position_size

def close_futures_position(account, symbol, position_info):
    """
    平仓合约持仓
    
    Args:
        account: 交易账户实例
        symbol: 交易对
        position_info: 持仓信息
    
    Returns:
        dict: 平仓订单结果
    """
    try:
        if position_info and position_info['size'] != 0:
            # 平仓方向与开仓相反
            is_short = _is_short_position(position_info)
            close_side = 'buy' if is_short else 'sell'
            pos_side = 'short' if is_short else 'long'
            close_amount = abs(position_info['size'])
            
            # 合约交易对格式转换
            # 从 BTC-USDT-SWAP 转换为 BTC-USDT
            if symbol.endswith('-SWAP'):
                symbol_for_trade = symbol.replace('-SWAP', '')
            else:
                symbol_for_trade = symbol
            
            # 确保使用正确的合约交易对格式
            if not symbol_for_trade.endswith('-SWAP'):
                symbol_for_trade = f"{symbol_for_trade}-SWAP"
            
            order = account.exchange.create_order(
                symbol=symbol_for_trade,
                type="market",
                side=close_side,
                amount=close_amount,
                params={
                    'instType': 'SWAP',
                    'tdMode': 'isolated',
                    'posSide': pos_side
                }
            )
            
            return order
        return None
    except Exception as e:
        logging.error(f"平仓失败: {e}")
        return None

def _close_position(account, symbol, position_info, price, position_type):
    """平仓辅助函数"""
    try:
        print(f"🔄 正在执行平仓订单...")
        order = close_futures_position(account, symbol, position_info)
        if order:
            print(f"\n✅ 合约平仓成功!")
            print(f"📋 订单信息:")
            print(f"  订单ID: {order.get('id', 'N/A')}")
            print(f"  状态: {order.get('status', 'N/A')}")
            print(f"  平仓价格: {price:.2f} USDT")
            print(f"  平仓数量: {abs(position_info['size']):.4f} 张")
            is_short = _is_short_position(position_info)
            print(f"  交易方向: {'做空平仓' if is_short else '做多平仓'}")
            
            # 计算实际盈亏
            entry_price = position_info['entry_price']
            position_size = abs(position_info['size'])
            if is_short:
                actual_pnl = (entry_price - price) * position_size
            else:
                actual_pnl = (price - entry_price) * position_size
            
            # 基于保证金计算收益率
            margin_used = CONTRACT_CONFIG["fixed_margin"]  # 固定保证金
            pnl_pct_vs_margin = (actual_pnl / margin_used) * 100
            print(f"💰 交易结果:")
            print(f"  入场价格: {entry_price:.2f} USDT")
            print(f"  平仓价格: {price:.2f} USDT")
            print(f"  实际盈亏: {actual_pnl:.2f} USDT")
            print(f"  保证金收益率: {pnl_pct_vs_margin:.2f}%")
            print(f"  保证金: {margin_used} USDT")
            
            return True
        else:
            print("❌ 合约平仓失败")
            return False
            
    except Exception as e:
        print(f"❌ 合约平仓失败: {str(e)}")
        return False

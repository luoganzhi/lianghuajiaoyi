import ccxt
import pandas as pd
from typing import Dict, Optional, Union, List
from .base_executor import BaseExecutor
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class OKXExecutor(BaseExecutor):
    """OKX交易所交易执行器"""
    
    def __init__(self, api_key: str, api_secret: str, api_password: str, proxy: Optional[str] = None, is_simulated: bool = True):
        """
        初始化OKX交易执行器
        Args:
            api_key: OKX API Key
            api_secret: OKX API Secret
            api_password: OKX API Password
            proxy: 代理服务器地址，例如 "http://127.0.0.1:7890"
            is_simulated: 是否使用模拟盘，默认为True
        """
        super().__init__('okx', api_key, api_secret, proxy)
        # 配置代理
        exchange_config = {
            'apiKey': api_key,
            'secret': api_secret,
            'password': api_password,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'swap'  # 使用合约API
            }
        }
        
        # 添加代理配置
        if proxy:
            exchange_config['proxies'] = {
                'http': proxy,
                'https': proxy
            }
            print(f"🔧 使用代理: {proxy}")
        
        self.exchange = ccxt.okx(exchange_config)
        # 强制切换到sandbox（模拟盘）环境
        if is_simulated:
            self.exchange.options['sandbox'] = True
            self.exchange.set_sandbox_mode(True)
        logger.info(f"OKX交易执行器初始化完成 (模拟盘: {'是' if is_simulated else '否'})")

    @staticmethod
    def _to_okx_swap_inst_id(symbol: str) -> str:
        """Normalize a symbol to OKX's SWAP instrument id, e.g. BTC-USDT-SWAP."""
        normalized = symbol.split(':', 1)[0].replace('/', '-')
        if not normalized.endswith('-SWAP'):
            normalized = f"{normalized}-SWAP"
        return normalized
        
    def place_order(self, symbol: str, order_type: str, side: str, 
                   amount: float, price: Optional[float] = None) -> Dict:
        """
        下单
        Args:
            symbol: 交易对
            order_type: 订单类型（limit/market）
            side: 买卖方向（buy/sell）
            amount: 数量
            price: 价格（市价单可为None）
        Returns:
            订单信息字典
        """
        try:
            order = self.exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=amount,
                price=price
            )
            logger.info(f"下单成功: {order}")
            return order
        except Exception as e:
            logger.error(f"下单失败: {str(e)}")
            raise
    
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        撤单
        Args:
            order_id: 订单ID
            symbol: 交易对
        Returns:
            是否成功
        """
        try:
            result = self.exchange.cancel_order(order_id, symbol)
            logger.info(f"撤单成功: {result}")
            return True
        except Exception as e:
            logger.error(f"撤单失败: {str(e)}")
            return False
    
    def get_order(self, order_id: str, symbol: str) -> Dict:
        """
        查询订单
        Args:
            order_id: 订单ID
            symbol: 交易对
        Returns:
            订单信息字典
        """
        try:
            order = self.exchange.fetch_order(order_id, symbol)
            return order
        except Exception as e:
            logger.error(f"查询订单失败: {str(e)}")
            raise
    
    def get_orders(self, symbol: str, status: str = None) -> List[Dict]:
        """
        查询订单列表
        Args:
            symbol: 交易对
            status: 订单状态（open/closed）
        Returns:
            订单信息列表
        """
        try:
            orders = []
            if status == 'open' or status is None:
                open_orders = self.exchange.fetch_open_orders(symbol)
                orders.extend(open_orders)
            if status == 'closed' or status is None:
                closed_orders = self.exchange.fetch_closed_orders(symbol)
                orders.extend(closed_orders)
            logger.info(f"获取{symbol}订单列表成功")
            return orders
        except Exception as e:
            logger.error(f"查询订单列表失败: {str(e)}")
            raise
    
    def get_position(self, symbol: str) -> Dict:
        """
        查询持仓
        Args:
            symbol: 交易对
        Returns:
            持仓信息字典
        """
        inst_id = self._to_okx_swap_inst_id(symbol)
        try:
            params = {
                'instType': 'SWAP',
                'instId': inst_id,
            }
            logger.debug(f"持仓查询参数: {params}")
            positions = self.exchange.privateGetAccountPositions(params)
            logger.debug(f"持仓查询响应: {positions}")

            if positions and positions.get('code') == '0' and 'data' in positions and positions['data']:
                # 遍历所有持仓，找到有持仓的
                for position in positions['data']:
                    pos_size = float(position.get('pos', 0))
                    if pos_size != 0:  # 找到有持仓的（包括正数和负数）
                        logger.info(f"获取{symbol}持仓成功 (原生API)")
                        
                        # 正确解析持仓方向
                        pos_side = position.get('posSide', '')
                        position_type = 'long' if pos_side == 'long' else 'short' if pos_side == 'short' else 'unknown'
                        
                        # 根据持仓数量确定持仓类型
                        position_type = 'short' if pos_size < 0 else 'long' if pos_size > 0 else 'unknown'
                        
                        return {
                            'symbol': inst_id,
                            'size': abs(pos_size),  # 使用绝对值作为持仓数量
                            'entry_price': float(position['avgPx']) if position['avgPx'] else 0.0,
                            'unrealized_pnl': float(position['upl']) if position['upl'] else 0.0,
                            'leverage': float(position['lever']) if position['lever'] else 1.0,
                            'margin_mode': position['mgnMode'] if position['mgnMode'] else 'isolated',
                            'posSide': pos_side,  # 添加持仓方向
                            'position_type': position_type,  # 根据持仓数量确定的持仓类型
                            'info': position
                        }
                
                # 如果没有找到有持仓的，返回空
                logger.debug(f"未找到{inst_id}的有效持仓")
                return {}
            else:
                logger.debug(f"未找到{inst_id}的持仓数据: {positions}")
                return {}
                
        except Exception as e:
            logger.error(f"查询持仓失败: {str(e)}")
            print(f"❌ 持仓查询API调用失败: {str(e)}")
            print(f"🔧 错误类型: {type(e).__name__}")
            if hasattr(e, 'args'):
                print(f"🔧 错误详情: {e.args}")
            return {}
    
    def get_balance(self, currency: str) -> Optional[float]:
        """
        获取账户余额
        Args:
            currency: 货币类型，如 'USDT', 'BTC'
        Returns:
            余额数量
        """
        try:
            # 使用OKX的账户余额API
            # 对于合约交易，需要查询交易账户余额
            balance_response = self.exchange.privateGetAccountBalance({'ccy': currency})
            
            if balance_response and balance_response.get('code') == '0':
                data = balance_response.get('data', [])
                if data:
                    details = data[0].get('details', [])
                    for detail in details:
                        if detail.get('ccy') == currency:
                            # 返回可用余额
                            avail_bal = float(detail.get('availBal', '0'))
                            logger.info(f"获取{currency}余额成功: {avail_bal}")
                            return avail_bal
                    
                    # 如果没有找到该货币，返回0
                    logger.info(f"未找到{currency}余额，返回0")
                    return 0.0
                else:
                    logger.warning("余额数据为空")
                    return 0.0
            else:
                logger.error(f"获取余额API调用失败: {balance_response}")
                return None
                
        except Exception as e:
            logger.error(f"获取余额失败: {type(e).__name__}: {str(e)}")
            if hasattr(e, 'args'):
                logger.error(f"余额错误详情: {e.args}")
            return None
    
    def set_leverage(self, symbol: str, leverage: int) -> bool:
        """
        设置合约杠杆倍数
        Args:
            symbol: 交易对，如 'BTC-USDT'
            leverage: 杠杆倍数
        Returns:
            是否成功
        """
        try:
            # 对于OKX，需要将symbol转换为正确的格式
            # 如果是永续合约，需要添加-SWAP后缀
            if not symbol.endswith('-SWAP'):
                symbol = f"{symbol}-SWAP"
            
            # 设置杠杆倍数
            print(f"🔧 OKX API - 设置杠杆: {symbol} {leverage}x")
            
            # 使用OKX的私有API设置杠杆
            # 简化设置，不指定posSide，让API自动处理
            try:
                result = self.exchange.privatePostAccountSetLeverage({
                    'instId': symbol,
                    'lever': str(leverage),
                    'mgnMode': 'isolated'
                    # 不设置posSide，让API自动处理
                })
                print(f"🔧 OKX API - 杠杆设置结果: {result}")
                
                if result and result.get('code') == '0':
                    logger.info(f"设置杠杆成功: {symbol} {leverage}x")
                    return True
                else:
                    logger.error(f"设置杠杆失败: {result}")
                    return False
                    
            except Exception as e:
                logger.error(f"设置杠杆异常: {str(e)}")
                return False
        except Exception as e:
            logger.error(f"设置杠杆失败: {str(e)}")
            return False
    
    def get_ticker(self, symbol: str) -> Dict:
        """
        获取最新行情
        Args:
            symbol: 交易对
        Returns:
            行情信息字典
        """
        try:
            # 使用公共API获取行情
            ticker = self.exchange.publicGetMarketTicker({'instId': symbol})
            if ticker and 'data' in ticker and len(ticker['data']) > 0:
                data = ticker['data'][0]
                result = {
                    'symbol': symbol,
                    'last': float(data['last']),
                    'bid': float(data['bidPx']),
                    'ask': float(data['askPx']),
                    'high': float(data['high24h']),
                    'low': float(data['low24h']),
                    'volume': float(data['vol24h']),
                    'timestamp': int(data['ts']),
                    'datetime': datetime.fromtimestamp(int(data['ts'])/1000).isoformat(),
                    'info': data
                }
                logger.info(f"获取{symbol}行情成功")
                return result
            raise Exception("获取行情数据为空")
        except Exception as e:
            logger.error(f"获取行情失败: {str(e)}")
            raise
    
    def update_positions(self):
        """更新持仓信息"""
        try:
            positions = self.exchange.fetch_positions()
            self.positions = {pos['symbol']: pos for pos in positions}
        except Exception as e:
            logger.error(f"更新持仓信息失败: {str(e)}")
    
    def update_orders(self):
        """更新订单信息"""
        try:
            orders = self.exchange.fetch_open_orders()
            self.orders = {order['id']: order for order in orders}
        except Exception as e:
            logger.error(f"更新订单信息失败: {str(e)}")

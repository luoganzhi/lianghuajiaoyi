import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.execution.okx_executor import OKXExecutor
import logging
from datetime import datetime
import traceback
from config.config import IS_SIMULATED, SIM_API_KEY, SIM_API_SECRET, SIM_API_PASSWORD, REAL_API_KEY, REAL_API_SECRET, REAL_API_PASSWORD, PROXY
import ccxt

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_order():
    try:
        # 根据配置文件选择API参数
        if IS_SIMULATED:
            api_key = SIM_API_KEY
            api_secret = SIM_API_SECRET
            api_password = SIM_API_PASSWORD
            logger.info("当前为模拟盘环境")
        else:
            api_key = REAL_API_KEY
            api_secret = REAL_API_SECRET
            api_password = REAL_API_PASSWORD
            logger.info("当前为实盘环境")
        proxy = PROXY
        logger.info("正在初始化交易执行器...")
        executor = OKXExecutor(
            api_key=api_key, 
            api_secret=api_secret, 
            api_password=api_password,
            proxy=proxy,
            is_simulated=IS_SIMULATED
        )
        
        # 测试交易对
        symbol = "BTC-USDT"
        
        # 测试市价单
        logger.info("测试市价单下单...")
        try:
            # 获取当前市价
            ticker = executor.get_ticker(symbol)
            current_price = float(ticker['last'])
            logger.info(f"当前BTC价格: {current_price} USDT")
            
            # 计算最小交易金额（约10 USDT）
            amount = 0.0001  # 买入0.0001 BTC，约10 USDT
            
            # 下买单（市价）
            order = executor.place_order(
                symbol=symbol,
                order_type='market',
                side='buy',
                amount=amount
            )
            logger.info(f"市价单下单成功: {order}")
            
            # 等待5秒
            import time
            time.sleep(5)
            
            # 查询订单状态
            order_id = order['id']
            order_info = executor.get_order(order_id, symbol)
            logger.info(f"订单状态: {order_info['status']}")
            
            # 查询最新余额
            balance = executor.get_balance("USDT")
            logger.info(f"当前USDT余额: {balance}")
            
            # 查询BTC余额
            btc_balance = executor.get_balance("BTC")
            logger.info(f"当前BTC余额: {btc_balance}")
            
        except Exception as e:
            logger.error(f"市价单测试失败: {str(e)}")
            logger.error(f"错误详情: {traceback.format_exc()}")
        
        logger.info("下单测试完成！")
        return True
        
    except Exception as e:
        logger.error(f"测试过程中出现错误: {str(e)}")
        logger.error(f"错误详情: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    test_order() 
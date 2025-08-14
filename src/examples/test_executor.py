import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.execution.okx_executor import OKXExecutor
import logging
from datetime import datetime
import pandas as pd
import traceback

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_executor():
    try:
        # # 初始化交易执行器
        # api_key = "fa953a81-9a4e-4d5f-9127-358e77368607"  # 替换为你的API密钥
        # api_secret = "15307FBF0164CF622D51E05DDA2BE7C8"  # 替换为你的API密钥对应的密钥
        # api_password = "!qwer1234QWER"  # 替换为你的API密码
        api_key = "48b64404-aff0-415e-9820-f9a55a3d8690"
        api_secret = "83B2A5C7AEB8DB8EA71BF72C4AB886C5"
        api_password = "!qwer1234QWER"
        proxy = "http://127.0.0.1:7890"

        
        logger.info("正在初始化交易执行器...")
        executor = OKXExecutor(
            api_key=api_key, 
            api_secret=api_secret, 
            api_password=api_password,
            proxy=proxy
        )
        
        # 测试获取行情
        symbol = "BTC-USDT"
        logger.info(f"正在获取{symbol}行情...")
        try:
            ticker = executor.get_ticker(symbol)
            logger.info(f"获取行情成功: {ticker}")
        except Exception as e:
            logger.error(f"获取行情失败: {str(e)}")
            logger.error(f"错误详情: {traceback.format_exc()}")
            return False
        
        # 测试查询余额
        logger.info("正在查询USDT余额...")
        try:
            balance = executor.get_balance("USDT")
            logger.info(f"查询余额成功: {balance}")
        except Exception as e:
            logger.error(f"查询余额失败: {str(e)}")
            logger.error(f"错误详情: {traceback.format_exc()}")
            return False
        
        # 测试查询持仓
        logger.info(f"正在查询{symbol}持仓...")
        try:
            position = executor.get_position(symbol)
            logger.info(f"查询持仓成功: {position}")
        except Exception as e:
            logger.error(f"查询持仓失败: {str(e)}")
            logger.error(f"错误详情: {traceback.format_exc()}")
            return False
        
        # 测试查询订单
        logger.info(f"正在查询{symbol}订单...")
        try:
            orders = executor.get_orders(symbol)
            logger.info(f"查询订单成功: {orders}")
        except Exception as e:
            logger.error(f"查询订单失败: {str(e)}")
            logger.error(f"错误详情: {traceback.format_exc()}")
            return False
        
        logger.info("交易执行器测试完成！")
        return True
    except Exception as e:
        logger.error(f"测试过程中出现错误: {str(e)}")
        logger.error(f"错误详情: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    test_executor() 
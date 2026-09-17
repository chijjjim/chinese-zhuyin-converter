import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

class Config:
    """應用程式配置"""
    
    # Flask 設定
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    DEBUG = os.getenv('FLASK_DEBUG', 'False') == 'True'
    
    # Gemini API
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    
    # MySQL 資料庫設定
    DB_CONFIG = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 3306)),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
        'database': os.getenv('DB_NAME', 'zhuyin_converter'),
        'charset': 'utf8mb4',
        'cursorclass': 'DictCursor'
    }
    
    @staticmethod
    def get_db_config():
        """取得資料庫配置"""
        return Config.DB_CONFIG
    
    @staticmethod
    def validate():
        """驗證配置是否完整"""
        if not Config.GEMINI_API_KEY:
            raise ValueError("找不到 GEMINI_API_KEY，請檢查 .env 檔案")
        
        if not Config.DB_CONFIG['password']:
            print("警告：資料庫密碼為空")
        
        print("配置驗證通過")
"""
初始化資料庫
建立必要的表格
"""

import sys
import os

# 將 backend 目錄加入 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
from config import Config

def create_database():
    """建立資料庫（如果不存在）"""
    db_config = Config.get_db_config()
    
    # 先連接到 MySQL（不指定資料庫）
    connection = pymysql.connect(
        host=db_config['host'],
        port=db_config['port'],
        user=db_config['user'],
        password=db_config['password'],
        charset='utf8mb4'
    )
    
    try:
        with connection.cursor() as cursor:
            # 建立資料庫
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_config['database']} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"資料庫 '{db_config['database']}' 已建立或已存在")
        
        connection.commit()
    finally:
        connection.close()

def create_tables():
    """建立資料表"""
    db_config = Config.get_db_config()
    
    # 連接到指定的資料庫
    connection = pymysql.connect(
        host=db_config['host'],
        port=db_config['port'],
        user=db_config['user'],
        password=db_config['password'],
        database=db_config['database'],
        charset='utf8mb4'
    )
    
    try:
        with connection.cursor() as cursor:
            # 1. 建立 zhuyin 表（注音對照表）
            print("\n建立 zhuyin 表...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS zhuyin (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    hanzi VARCHAR(10) NOT NULL COMMENT '中文字',
                    cns VARCHAR(20) COMMENT 'CNS 編碼',
                    unicode_code VARCHAR(10) COMMENT 'Unicode 編碼',
                    bpmf TEXT COMMENT '注音（多個注音用分號分隔）',
                    quantity INT DEFAULT 0 COMMENT '注音數量',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_hanzi (hanzi),
                    INDEX idx_cns (cns)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("   zhuyin 表建立完成")
            
            # 2. 建立 users 表（使用者表）
            print("\n建立 users 表...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) NOT NULL UNIQUE COMMENT '使用者名稱',
                    password_hash VARCHAR(255) NOT NULL COMMENT '密碼雜湊'
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("   users 表建立完成")
            print("   conversion_history 表建立完成")
        
        connection.commit()
        print("\n所有資料表建立完成！")
        
    finally:
        connection.close()

def init_database():
    """初始化整個資料庫"""
    print("=" * 60)
    print("開始初始化資料庫")
    print("=" * 60)
    
    try:
        # 1. 建立資料庫
        create_database()
        
        # 2. 建立資料表
        create_tables()
        
        print("\n" + "=" * 60)
        print("資料庫初始化完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n資料庫初始化失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    init_database()
import pymysql
from pymysql.cursors import DictCursor
from config import Config

class Database:
    """資料庫連線管理"""
    
    def __init__(self):
        self.connection = None
    
    def connect(self):
        """建立資料庫連線"""
        try:
            db_config = Config.get_db_config()
            self.connection = pymysql.connect(
                host=db_config['host'],
                port=db_config['port'],
                user=db_config['user'],
                password=db_config['password'],
                database=db_config['database'],
                charset=db_config['charset'],
                cursorclass=DictCursor
            )
            print("資料庫連線成功")
            return self.connection
        except pymysql.MySQLError as e:
            print(f"資料庫連線失敗: {e}")
            raise
    
    def close(self):
        """關閉資料庫連線"""
        if self.connection:
            self.connection.close()
            print("資料庫連線已關閉")
    
    def execute_query(self, query, params=None):
        """
        執行 SQL 查詢
        
        Args:
            query: SQL 查詢語句
            params: 參數（可選）
            
        Returns:
            查詢結果
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                self.connection.commit()
                return cursor.fetchall()
        except pymysql.MySQLError as e:
            self.connection.rollback()
            print(f"SQL 執行失敗: {e}")
            raise
    
    def execute_many(self, query, data_list):
        """
        批次執行 SQL（用於大量插入）
        
        Args:
            query: SQL 語句
            data_list: 資料列表
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.executemany(query, data_list)
                self.connection.commit()
                return cursor.rowcount
        except pymysql.MySQLError as e:
            self.connection.rollback()
            print(f"批次執行失敗: {e}")
            raise

def get_db_connection():
    """取得資料庫連線（工廠函式）"""
    db_config = Config.get_db_config()
    return pymysql.connect(
        host=db_config['host'],
        port=db_config['port'],
        user=db_config['user'],
        password=db_config['password'],
        database=db_config['database'],
        charset=db_config['charset'],
        cursorclass=DictCursor
    )
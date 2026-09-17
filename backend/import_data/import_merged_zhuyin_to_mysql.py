"""
將 merged_zhuyin.csv 匯入 MySQL
"""

import sys
import os

# 將 backend 目錄加入路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import pymysql
from config import Config

def import_csv_to_mysql(csv_path):
    """
    將 CSV 匯入 MySQL
    
    Args:
        csv_path: CSV 檔案路徑
    """
    print("=" * 60)
    print("📥 開始匯入資料到 MySQL")
    print("=" * 60)
    
    # 1. 讀取 CSV
    print(f"\n📖 讀取 CSV: {csv_path}")
    
    if not os.path.exists(csv_path):
        print(f"❌ 找不到檔案: {csv_path}")
        return
    
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    print(f"   共 {len(df)} 行資料")
    print(f"   欄位: {list(df.columns)}")
    
    # 2. 連接資料庫
    print(f"\n🔌 連接資料庫...")
    db_config = Config.get_db_config()
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
            # 3. 清空舊資料（可選）
            print(f"\n🗑️  清空舊資料...")
            cursor.execute("DELETE FROM zhuyin")
            connection.commit()
            print(f"   ✅ 已清空")
            
            # 4. 準備資料
            print(f"\n📦 準備匯入資料...")
            insert_query = """
                INSERT INTO zhuyin (hanzi, cns, unicode_code, bpmf, quantity)
                VALUES (%s, %s, %s, %s, %s)
            """
            
            data_list = []
            skipped = 0
            
            for idx, row in df.iterrows():
                # 處理國字（可能在不同欄位）
                hanzi = None
                if '國字' in df.columns:
                    hanzi = str(row['國字']).strip() if pd.notna(row['國字']) else ''
                elif 'hanzi' in df.columns:
                    hanzi = str(row['hanzi']).strip() if pd.notna(row['hanzi']) else ''
                
                if not hanzi or hanzi == 'nan' or hanzi == '':
                    skipped += 1
                    continue
                
                cns = str(row['CNS']).strip() if 'CNS' in df.columns and pd.notna(row['CNS']) else ''
                unicode_code = str(row['Unicode']).strip() if 'Unicode' in df.columns and pd.notna(row['Unicode']) else ''
                bpmf = str(row['注音']).strip() if '注音' in df.columns and pd.notna(row['注音']) else ''
                quantity = int(row['注音數量']) if '注音數量' in df.columns and pd.notna(row['注音數量']) else 0
                
                data_list.append((hanzi, cns, unicode_code, bpmf, quantity))
            
            print(f"   有效資料: {len(data_list)} 筆")
            print(f"   跳過資料: {skipped} 筆")
            
            # 5. 批次插入（每次 1000 筆）
            print(f"\n💾 開始匯入 {len(data_list)} 筆資料...")
            batch_size = 1000
            total_inserted = 0
            
            for i in range(0, len(data_list), batch_size):
                batch = data_list[i:i + batch_size]
                cursor.executemany(insert_query, batch)
                connection.commit()
                total_inserted += len(batch)
                
                # 顯示進度
                progress = (total_inserted / len(data_list)) * 100
                print(f"   進度: {total_inserted}/{len(data_list)} ({progress:.1f}%)")
            
            print(f"\n✅ 成功匯入 {total_inserted} 筆資料")
            
            # 6. 驗證資料
            print(f"\n🔍 驗證資料...")
            cursor.execute("SELECT COUNT(*) as total FROM zhuyin")
            result = cursor.fetchone()
            print(f"   資料庫中共有 {result[0]} 筆資料")
            
            cursor.execute("SELECT COUNT(*) as total FROM zhuyin WHERE quantity > 1")
            result = cursor.fetchone()
            print(f"   多音字: {result[0]} 個")
            
            # 顯示範例
            print(f"\n📝 資料範例（多音字前 5 筆）:")
            cursor.execute("SELECT hanzi, cns, bpmf, quantity FROM zhuyin WHERE quantity > 1 LIMIT 5")
            rows = cursor.fetchall()
            for row in rows:
                print(f"   {row[0]} ({row[1]}): {row[2]} ({row[3]}個讀音)")
        
        print("\n" + "=" * 60)
        print("✅ 資料匯入完成！")
        print("=" * 60)
        
    except Exception as e:
        connection.rollback()
        print(f"\n❌ 匯入失敗: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        connection.close()

if __name__ == "__main__":
    # CSV 檔案路徑（請根據實際位置修改）
    csv_paths = [
        "merged_zhuyin.csv",
        "../merged_zhuyin.csv",
        "../../merged_zhuyin.csv",
        r"C:\Users\USER\Desktop\國科會\chinese-zhuyin-converter_v1\backend\scripts\merged_zhuyin.csv"
    ]
    
    csv_path = None
    for path in csv_paths:
        if os.path.exists(path):
            csv_path = path
            break
    
    if csv_path is None:
        print("❌ 找不到 merged_zhuyin.csv")
        print("\n可能的位置:")
        for p in csv_paths:
            print(f"   - {os.path.abspath(p)}")
        
        print("\n請手動指定檔案路徑:")
        user_path = input("CSV 檔案路徑: ").strip()
        if os.path.exists(user_path):
            csv_path = user_path
        else:
            print(f"❌ 找不到檔案: {user_path}")
            sys.exit(1)
    
    import_csv_to_mysql(csv_path)
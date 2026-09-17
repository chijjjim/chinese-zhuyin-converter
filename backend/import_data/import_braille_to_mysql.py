"""
將 braille CSV 匯入 MySQL
支援：注音、數字、英文、中文標點、英文標點、縮寫詞
"""

import sys
import os

# 將 backend 目錄加入路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import pymysql
from config import Config

# ============================================================
# 類型定義
# ============================================================

# 注音聲母
INITIALS = ['ㄅ', 'ㄆ', 'ㄇ', 'ㄈ', 'ㄉ', 'ㄊ', 'ㄋ', 'ㄌ',
            'ㄍ', 'ㄎ', 'ㄏ', 'ㄐ', 'ㄑ', 'ㄒ',
            'ㄓ', 'ㄔ', 'ㄕ', 'ㄖ', 'ㄗ', 'ㄘ', 'ㄙ']

# 注音韻母
FINALS = ['ㄚ', 'ㄛ', 'ㄜ', 'ㄝ', 'ㄞ', 'ㄟ', 'ㄠ', 'ㄡ',
          'ㄢ', 'ㄣ', 'ㄤ', 'ㄥ', 'ㄦ']

# 注音介母
MEDIALS = ['ㄧ', 'ㄨ', 'ㄩ']

# 注音結合韻
COMPOUND_FINALS = [
    'ㄧㄚ', 'ㄧㄛ', 'ㄧㄝ', 'ㄧㄞ', 'ㄧㄠ', 'ㄧㄡ', 'ㄧㄢ', 'ㄧㄣ', 'ㄧㄤ', 'ㄧㄥ',
    'ㄨㄚ', 'ㄨㄛ', 'ㄨㄞ', 'ㄨㄟ', 'ㄨㄢ', 'ㄨㄣ', 'ㄨㄤ', 'ㄨㄥ',
    'ㄩㄝ', 'ㄩㄢ', 'ㄩㄣ', 'ㄩㄥ'
]

# 注音聲調
TONES = ['ˊ', 'ˇ', 'ˋ', '˙', '一聲']

# 數字
DIGITS = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']

# 英文字母（小寫）
ENGLISH_LETTERS = list('abcdefghijklmnopqrstuvwxyz')

# 中文標點符號（包含單獨的和成對的）
CHINESE_PUNCTS = ['。', '？', '！', '，', '、', '；', '：', '．',
                  '……', '──', '「 」', '『 』', '（　）', '──　──',
                  '＿＿', '﹏﹏', '※', '◎', '［　］', '｛　｝',
                  # 單獨的中文標點
                  '「', '」', '『', '』', '（', '）', '［', '］', '｛', '｝']

# 英文標點符號（包含單獨的和成對的）
ENGLISH_PUNCTS = ['","', ';', ':', '.', '!', '( )', '?', "'", '*', '…', '-', '──', '[ ]', '" "', "' '",
                  # 單獨的英文標點
                  '(', ')', '[', ']', '"', '"', ''', ''']

# 特殊符號
NUMBER_PREFIX = '數字記號'
DECIMAL_POINT = '小數點記號'
CAPITAL_PREFIX = '大寫'


def get_bpmf_type(bpmf):
    """
    判斷符號類型

    Returns:
        str: 類型名稱
    """
    bpmf = str(bpmf).strip()

    # 空值檢查
    if not bpmf or bpmf == 'nan':
        return None

    # 1. 注音類型
    if bpmf in INITIALS:
        return 'initial'
    if bpmf in COMPOUND_FINALS:
        return 'compound'
    if bpmf in MEDIALS:
        return 'medial'
    if bpmf in FINALS:
        return 'final'
    if bpmf in TONES or bpmf == '':  # 空白表示一聲
        return 'tone'

    # 2. 數字類型
    if bpmf in DIGITS:
        return 'digit'
    if bpmf == NUMBER_PREFIX or bpmf == DECIMAL_POINT:
        return 'number_prefix'

    # 3. 英文類型
    if bpmf.lower() in ENGLISH_LETTERS:
        return 'english'
    if bpmf == CAPITAL_PREFIX:
        return 'capital_prefix'

    # 4. 標點類型
    if bpmf in CHINESE_PUNCTS:
        return 'chinese_punct'
    if bpmf in ENGLISH_PUNCTS:
        return 'english_punct'

    # 5. 縮寫詞（英文單字）
    if bpmf.isalpha() and len(bpmf) > 1:
        return 'abbreviation'

    # 6. 包含空格的配對標點
    if ' ' in bpmf or '　' in bpmf:
        # 判斷是中文還是英文標點
        if any(ord(c) > 127 for c in bpmf):
            return 'chinese_punct'
        else:
            return 'english_punct'

    return None


def import_braille_to_mysql(csv_path):
    """
    將 braille CSV 匯入 MySQL

    Args:
        csv_path: CSV 檔案路徑
    """
    print("=" * 60)
    print("開始匯入點字資料到 MySQL")
    print("=" * 60)

    # 1. 讀取 CSV
    print(f"\n讀取 CSV: {csv_path}")

    if not os.path.exists(csv_path):
        print(f"找不到檔案: {csv_path}")
        return

    # 使用預設 quoting 以正確處理包含逗號的欄位（如 "," 標點符號）
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    print(f"   共 {len(df)} 行資料")
    print(f"   欄位: {list(df.columns)}")

    # 2. 連接資料庫
    print(f"\n連接資料庫...")
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
            # 3. 清空舊資料
            print(f"\n清空舊資料...")
            cursor.execute("DELETE FROM braille")
            connection.commit()
            print(f"   已清空")

            # 4. 準備資料
            print(f"\n準備匯入資料...")
            # 使用 INSERT IGNORE 忽略重複的條目
            insert_query = """
                INSERT IGNORE INTO braille (bpmf, unicode_code, braille_char, n_value, e_value, bpmf_type)
                VALUES (%s, %s, %s, %s, %s, %s)
            """

            data_list = []
            seen_bpmf = set()  # 追蹤已見過的 bpmf，避免重複
            skipped = 0
            duplicates = 0
            type_count = {}

            for idx, row in df.iterrows():
                bpmf = str(row['bpmf']).strip() if pd.notna(row['bpmf']) else ''

                if not bpmf or bpmf == 'nan':
                    skipped += 1
                    continue

                # 跳過重複的 bpmf
                if bpmf in seen_bpmf:
                    duplicates += 1
                    continue
                seen_bpmf.add(bpmf)

                unicode_code = str(row['Unicode']).strip() if pd.notna(row['Unicode']) else ''
                braille_char = str(row['braille']).strip() if pd.notna(row['braille']) else ''

                # n_value 可能為空
                try:
                    n_value = int(row['n_value']) if pd.notna(row['n_value']) and str(row['n_value']).strip() else None
                except (ValueError, TypeError):
                    n_value = None

                e_value = str(row['e_value']).strip() if pd.notna(row['e_value']) else ''

                # 判斷類型
                bpmf_type = get_bpmf_type(bpmf)

                # 統計類型數量
                type_name = bpmf_type if bpmf_type else '未分類'
                type_count[type_name] = type_count.get(type_name, 0) + 1

                data_list.append((bpmf, unicode_code, braille_char, n_value, e_value, bpmf_type))

            print(f"   有效資料: {len(data_list)} 筆")
            print(f"   跳過空值: {skipped} 筆")
            print(f"   跳過重複: {duplicates} 筆")

            # 5. 批次插入
            print(f"\n開始匯入 {len(data_list)} 筆資料...")

            for data in data_list:
                cursor.execute(insert_query, data)

            connection.commit()
            print(f"\n成功匯入 {len(data_list)} 筆資料")

            # 6. 顯示統計
            print(f"\n各類型數量（匯入前統計）:")
            for type_name, count in sorted(type_count.items()):
                print(f"   {type_name}: {count} 個")

            # 7. 驗證資料
            print(f"\n驗證資料...")
            cursor.execute("SELECT COUNT(*) as total FROM braille")
            result = cursor.fetchone()
            print(f"   資料庫中共有 {result[0]} 筆資料")

            # 顯示各類型數量
            cursor.execute("""
                SELECT bpmf_type, COUNT(*) as cnt
                FROM braille
                GROUP BY bpmf_type
                ORDER BY cnt DESC
            """)
            rows = cursor.fetchall()
            print(f"\n各類型數量（資料庫統計）:")
            for row in rows:
                type_name = row[0] if row[0] else '未分類'
                print(f"   {type_name}: {row[1]} 個")

            # 顯示範例
            print(f"\n資料範例:")

            # 注音範例
            cursor.execute("SELECT bpmf, braille_char, e_value, bpmf_type FROM braille WHERE bpmf_type IN ('initial', 'final', 'compound') LIMIT 5")
            print("  [注音]")
            for row in cursor.fetchall():
                print(f"    {row[0]} -> {row[1]} (type: {row[3]})")

            # 數字範例
            cursor.execute("SELECT bpmf, braille_char, e_value, bpmf_type FROM braille WHERE bpmf_type IN ('digit', 'number_prefix') LIMIT 5")
            print("  [數字]")
            for row in cursor.fetchall():
                print(f"    {row[0]} -> {row[1]} (type: {row[3]})")

            # 英文範例
            cursor.execute("SELECT bpmf, braille_char, e_value, bpmf_type FROM braille WHERE bpmf_type IN ('english', 'capital_prefix') LIMIT 5")
            print("  [英文]")
            for row in cursor.fetchall():
                print(f"    {row[0]} -> {row[1]} (type: {row[3]})")

            # 縮寫詞範例
            cursor.execute("SELECT bpmf, braille_char, e_value, bpmf_type FROM braille WHERE bpmf_type = 'abbreviation' LIMIT 5")
            print("  [縮寫詞]")
            for row in cursor.fetchall():
                print(f"    {row[0]} -> {row[1]} (type: {row[3]})")

        print("\n" + "=" * 60)
        print("點字資料匯入完成！")
        print("=" * 60)

    except Exception as e:
        connection.rollback()
        print(f"\n匯入失敗: {e}")
        import traceback
        traceback.print_exc()

    finally:
        connection.close()


if __name__ == "__main__":
    # 優先使用 scripts 資料夾內的 CSV
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_csv_path = os.path.join(script_dir, '點字_v2.csv')
    root_csv_path = r"C:\Users\USER\Desktop\國科會\點字_v2.csv"

    # 也可以使用命令列參數指定
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    elif os.path.exists(local_csv_path):
        csv_path = local_csv_path
    elif os.path.exists(root_csv_path):
        csv_path = root_csv_path
    else:
        print(f"找不到 CSV 檔案")
        print(f"請指定 CSV 檔案路徑:")
        print(f"  python import_braille_to_mysql.py <csv_path>")
        print(f"或將檔案放置於: {local_csv_path}")
        sys.exit(1)

    import_braille_to_mysql(csv_path)

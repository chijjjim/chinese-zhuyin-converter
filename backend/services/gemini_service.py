import os
import re
import google.generativeai as genai
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

class GeminiService:
    """Gemini API 服務類別"""
    
    def __init__(self):
        """初始化 Gemini API"""
        # 從環境變數讀取 API Key
        api_key = os.getenv('GEMINI_API_KEY')
        
        if not api_key:
            raise ValueError("找不到 GEMINI_API_KEY，請檢查 .env 檔案")
        
        # 設定 API Key
        genai.configure(api_key=api_key)
        
        # 建立模型（使用最新的 gemini-2.5-flash）
        self.model = genai.GenerativeModel('models/gemini-2.5-flash')
        
        print("Gemini API 初始化成功（使用 gemini-2.5-flash）")
    
    def chinese_to_zhuyin(self, text):
        # 建立 Prompt（提示詞）
        prompt = f"""
請將以下繁體中文逐字轉換為注音符號（ㄅㄆㄇㄈ），每個字的注音之間用空格分隔。

要求：
1. 只輸出注音，不要輸出其他說明文字
2. 忽略所有標點符號，只轉換中文字
3. 根據上下文判斷多音字的正確讀音
4. 使用完整的注音符號，包含聲調符號（ˊˇˋ˙）

範例：
輸入：我要學習。
輸出：ㄨㄛˇ ㄧㄠˋ ㄒㄩㄝˊ ㄒㄧˊ

現在請轉換：
{text}
"""
        
        try:
            # 呼叫 Gemini API
            response = self.model.generate_content(prompt)
            
            # 取得結果
            result = response.text.strip()
            
            # 移除可能的標點符號和多餘空格
            result = self._clean_result(result)
            
            print(f"轉換成功: {text} -> {result}")
            
            return result
            
        except Exception as e:
            print(f"API 呼叫失敗: {str(e)}")
            raise Exception(f"Gemini API 錯誤: {str(e)}")
    
    def _clean_result(self, result):
        # 移除常見的標點符號
        punctuation = '，。！？、；：「」『』（）《》〈〉【】,.!?;:\'"()[]{}…—'
        for p in punctuation:
            result = result.replace(p, '')
        
        # 移除多餘的空格（保留單個空格）
        result = ' '.join(result.split())
        
        return result.strip()
    
    def test_connection(self):
        """測試 API 連線"""
        try:
            test_text = "你好"
            result = self.chinese_to_zhuyin(test_text)
            print(f"測試成功: {test_text} -> {result}")
            return True
        except Exception as e:
            print(f"測試失敗: {str(e)}")
            return False
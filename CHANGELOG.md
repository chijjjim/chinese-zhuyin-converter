# 修改紀錄 (Changelog)

## [2026-02-08] Gemini API 批次處理優化

### 問題描述

原本的程式碼在處理混合文字時，會將文字分段（中文、英文、數字、標點等），每個中文段落會單獨呼叫一次 Gemini API。當文字中有很多標點符號分隔時，會產生大量的 API 請求，導致超過 Gemini API 的呼叫頻率限制。

**範例：**
```
輸入文字：「你好，世界！這是測試。請問，你好嗎？」

修改前的處理方式：
- 段落1: "你好" → 呼叫 Gemini API
- 段落2: "，" → 標點處理
- 段落3: "世界" → 呼叫 Gemini API
- 段落4: "！" → 標點處理
- 段落5: "這是測試" → 呼叫 Gemini API
- ... (每個中文段落都呼叫一次)

結果：一段短文就呼叫了 5+ 次 API
```

### 解決方案

改為「先收集所有中文字，再批次呼叫 Gemini API」的處理方式：

1. 先掃描整段文字，收集所有中文字
2. 批次查詢資料庫，找出哪些是多音字
3. 將所有中文字以 **500 字為單位** 分批發送給 Gemini API
4. 快取 Gemini 回傳的注音結果
5. 處理各段落時，直接使用快取的結果

### 修改檔案

**`backend/services/conversion_service.py`**

#### 新增常數

```python
# 批次處理的字數上限
BATCH_SIZE = 500
```

#### 新增方法

1. **`_batch_gemini_convert(self, all_chinese_text, all_chinese_chars)`**

   批次呼叫 Gemini API，每批處理 500 個字。

   ```python
   def _batch_gemini_convert(self, all_chinese_text, all_chinese_chars):
       """
       批次呼叫 Gemini API，每批處理 BATCH_SIZE 個字

       Args:
           all_chinese_text: 所有中文文字（保持上下文）
           all_chinese_chars: 所有中文字元列表

       Returns:
           dict: {f"{char}_{index}": zhuyin} 的對照表
       """
       # ... 實作內容
   ```

2. **`_convert_chinese_with_cache(self, text, char_info_map, gemini_zhuyin_map, start_index, include_braille)`**

   使用預先快取的 Gemini 結果來轉換中文文字。

   ```python
   def _convert_chinese_with_cache(self, text, char_info_map, gemini_zhuyin_map, start_index, include_braille=False):
       """
       使用預先快取的結果轉換中文文字

       Args:
           text: 中文文字
           char_info_map: 資料庫查詢結果
           gemini_zhuyin_map: Gemini API 結果
           start_index: 起始的全域字元索引
           include_braille: 是否包含點字

       Returns:
           list: 轉換結果列表
       """
       # ... 實作內容
   ```

#### 修改方法

**`convert_text(self, text, include_braille=False)`**

重新設計處理流程：

```python
def convert_text(self, text, include_braille=False):
    """
    轉換混合文字為注音/點字

    處理流程：
    1. 分段：將文字分為中文、英文、數字、標點等段落
    2. 收集所有中文字，批次呼叫 Gemini API（每批 500 字）
    3. 各段分別處理：
       - 中文：使用預先取得的 Gemini 結果 + 資料庫
       - 數字：直接轉點字（加數符）
       - 英文：直接轉點字（大寫加大寫符號）
       - 標點：直接轉點字
    """
    # ... 實作內容
```

#### 刪除方法

**`_convert_chinese(self, text, include_braille=False)`**

此方法已被 `_convert_chinese_with_cache` 取代，不再需要。

### 效能比較

| 情境 | 修改前 API 呼叫次數 | 修改後 API 呼叫次數 |
|------|---------------------|---------------------|
| 100 字文章（無標點） | 1 次 | 1 次 |
| 100 字文章（有 10 個標點） | 最多 11 次 | 1 次 |
| 500 字文章 | 依標點數量而定 | 1 次 |
| 1000 字文章 | 依標點數量而定 | 2 次 |
| 2000 字文章 | 依標點數量而定 | 4 次 |

### 日誌輸出

修改後會在 console 輸出批次處理的進度：

```
[Gemini] 批次處理: 字元 1 ~ 500 / 1200
[Gemini] 批次處理: 字元 501 ~ 1000 / 1200
[Gemini] 批次處理: 字元 1001 ~ 1200 / 1200
[Gemini] 總共處理 1200 個字，分 3 批
```

### 注意事項

1. `BATCH_SIZE` 預設為 500 字，可依據 Gemini API 的 token 限制調整
2. 如果某批次呼叫失敗，會記錄錯誤並繼續處理下一批
3. 只有在文字中包含多音字時才會呼叫 Gemini API
4. 非多音字直接使用資料庫的注音，不需要呼叫 API

---

## 版本資訊

- **修改日期**: 2026-02-08
- **修改者**: Claude AI Assistant
- **影響範圍**: `backend/services/conversion_service.py`
- **向後相容**: 是（API 介面不變）

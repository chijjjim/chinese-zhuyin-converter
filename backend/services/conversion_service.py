"""
轉換服務
支援中文（透過 Gemini）、英文、數字、標點符號的混合文字轉換
"""

import sys
import os
import re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.gemini_service import GeminiService
from services.braille_service import BrailleService
from database.db import get_db_connection


class ConversionService:
    """中文轉注音轉換服務（整合 Gemini + MySQL）"""

    # 中文標點符號（包含全形符號）
    CHINESE_PUNCTS = set('。？！，、；：．「」『』（）＿﹏※◎［］｛｝')

    # 英文標點符號（包含常用符號、彎曲引號）
    ENGLISH_PUNCTS = set(',.;:!?\'"()-[]{}*…─—''""-')

    # 特殊多字元標點（需要整體處理）
    MULTI_CHAR_PUNCTS = {'……', '──', '＿＿', '﹏﹏'}

    def __init__(self):
        """初始化服務"""
        # 初始化 Gemini API
        self.gemini = GeminiService()

        # 初始化點字服務
        self.braille_service = BrailleService()

        # 快取：儲存已查詢過的字
        self._cache = {}

        # 測試資料庫連線
        try:
            connection = get_db_connection()
            connection.close()
        except Exception as e:
            pass

    # ============================================================
    # 文字分段
    # ============================================================

    # 全形數字對照表
    FULLWIDTH_DIGITS = {'０': '0', '１': '1', '２': '2', '３': '3', '４': '4',
                        '５': '5', '６': '6', '７': '7', '８': '8', '９': '9'}

    def _get_char_type(self, char):
        """
        判斷單一字元的類型

        Args:
            char: 單一字元

        Returns:
            str: 'chinese', 'number', 'english', 'chinese_punct', 'english_punct', 'space', 'unknown'
        """
        # 空白
        if char.isspace():
            return 'space'

        # 數字（包含全形數字）
        if char.isdigit() or char in self.FULLWIDTH_DIGITS:
            return 'number'

        # 英文字母
        if char.isalpha() and ord(char) < 128:
            return 'english'

        # 中文標點
        if char in self.CHINESE_PUNCTS:
            return 'chinese_punct'

        # 英文標點
        if char in self.ENGLISH_PUNCTS:
            return 'english_punct'

        # 中文字（CJK 統一漢字範圍）
        if '\u4e00' <= char <= '\u9fff':
            return 'chinese'

        # 其他符號嘗試當作標點處理
        return 'unknown'

    def _segment_text(self, text):
        """
        將混合文字分段

        Args:
            text: 輸入文字

        Returns:
            list: [{'type': 'chinese', 'content': '你好'}, ...]
        """
        if not text:
            return []

        segments = []
        current_type = None
        current_content = ''

        for char in text:
            char_type = self._get_char_type(char)

            # 處理標點符號（每個單獨成段）
            if char_type in ('chinese_punct', 'english_punct'):
                # 先保存之前的段落
                if current_content:
                    segments.append({
                        'type': current_type,
                        'content': current_content
                    })
                    current_content = ''
                    current_type = None

                # 標點單獨成段
                segments.append({
                    'type': char_type,
                    'content': char
                })
                continue

            # 跳過空白（但可以用於分隔）
            if char_type == 'space':
                if current_content:
                    segments.append({
                        'type': current_type,
                        'content': current_content
                    })
                    current_content = ''
                    current_type = None
                continue

            # 類型相同，繼續累積
            if char_type == current_type:
                current_content += char
            else:
                # 類型不同，保存之前的段落
                if current_content:
                    segments.append({
                        'type': current_type,
                        'content': current_content
                    })
                current_type = char_type
                current_content = char

        # 保存最後的段落
        if current_content:
            segments.append({
                'type': current_type,
                'content': current_content
            })

        return segments

    # ============================================================
    # 主要轉換方法
    # ============================================================

    # 批次處理的字數上限
    BATCH_SIZE = 500

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

        Args:
            text: 要轉換的文字
            include_braille: 是否包含點字轉換
        """
        try:
            # 1. 分段
            segments = self._segment_text(text)

            # 2. 收集所有中文字並預先批次呼叫 Gemini
            all_chinese_chars = []
            chinese_segment_indices = []  # 記錄哪些段落是中文

            for idx, segment in enumerate(segments):
                if segment['type'] == 'chinese':
                    chinese_segment_indices.append(idx)
                    for char in segment['content']:
                        if self._is_chinese_char(char):
                            all_chinese_chars.append(char)

            # 3. 批次查詢資料庫，找出多音字
            char_info_map = self._batch_get_char_info(all_chinese_chars)

            # 4. 檢查是否有多音字需要使用 Gemini
            polyphone_chars = [char for char in all_chinese_chars
                             if char_info_map.get(char, {}).get('is_polyphone', False)]

            # 5. 預先批次呼叫 Gemini API（每批 500 字）
            gemini_zhuyin_map = {}
            if polyphone_chars:
                # 收集所有中文文字（保持原始順序和上下文）
                all_chinese_text = ''.join([seg['content'] for seg in segments if seg['type'] == 'chinese'])

                # 分批處理
                gemini_zhuyin_map = self._batch_gemini_convert(all_chinese_text, all_chinese_chars)

            # 6. 處理各段
            results = []
            global_char_index = 0  # 全域字元索引

            for segment in segments:
                seg_type = segment['type']
                seg_content = segment['content']

                if seg_type == 'chinese':
                    # 中文：使用預先取得的 Gemini 結果
                    chinese_results = self._convert_chinese_with_cache(
                        seg_content,
                        char_info_map,
                        gemini_zhuyin_map,
                        global_char_index,
                        include_braille
                    )
                    results.extend(chinese_results)
                    # 更新全域索引
                    global_char_index += len([c for c in seg_content if self._is_chinese_char(c)])

                elif seg_type == 'number':
                    # 數字：直接轉點字
                    number_result = self._convert_number(seg_content, include_braille)
                    results.append(number_result)

                elif seg_type == 'english':
                    # 英文：直接轉點字
                    english_result = self._convert_english(seg_content, include_braille)
                    results.append(english_result)

                elif seg_type in ('chinese_punct', 'english_punct'):
                    # 標點：直接轉點字
                    punct_result = self._convert_punctuation(seg_content, include_braille)
                    results.append(punct_result)

                elif seg_type == 'unknown':
                    # 未知類型：嘗試當作標點處理
                    punct_result = self._convert_punctuation(seg_content, include_braille)
                    results.append(punct_result)

            return {
                'original_text': text,
                'results': results,
                'success': True,
                'error_message': None,
                'include_braille': include_braille
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                'original_text': text,
                'results': [],
                'success': False,
                'error_message': str(e)
            }

    def _batch_gemini_convert(self, all_chinese_text, all_chinese_chars):
        """
        批次呼叫 Gemini API，每批處理 BATCH_SIZE 個字

        Args:
            all_chinese_text: 所有中文文字（保持上下文）
            all_chinese_chars: 所有中文字元列表

        Returns:
            dict: {f"{char}_{index}": zhuyin} 的對照表
        """
        gemini_zhuyin_map = {}
        total_chars = len(all_chinese_chars)

        if total_chars == 0:
            return gemini_zhuyin_map

        # 分批處理
        batch_start = 0
        global_index = 0

        while batch_start < total_chars:
            batch_end = min(batch_start + self.BATCH_SIZE, total_chars)

            # 取得這批次的文字（從原始文字中擷取對應的部分）
            batch_text = ''.join(all_chinese_chars[batch_start:batch_end])

            print(f"[Gemini] 批次處理: 字元 {batch_start+1} ~ {batch_end} / {total_chars}")

            try:
                # 呼叫 Gemini API
                gemini_result = self.gemini.chinese_to_zhuyin(batch_text)

                # 解析結果
                zhuyin_list = gemini_result.split()

                # 建立對照表
                for i, char in enumerate(all_chinese_chars[batch_start:batch_end]):
                    if i < len(zhuyin_list):
                        gemini_zhuyin_map[f"{char}_{global_index}"] = zhuyin_list[i]
                    global_index += 1

            except Exception as e:
                print(f"[Gemini] 批次處理失敗: {str(e)}")
                # 即使失敗也要更新索引
                global_index += (batch_end - batch_start)

            batch_start = batch_end

        print(f"[Gemini] 總共處理 {total_chars} 個字，分 {(total_chars + self.BATCH_SIZE - 1) // self.BATCH_SIZE} 批")

        return gemini_zhuyin_map

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
        results = []
        char_index = start_index

        for char in text:
            if not self._is_chinese_char(char):
                continue

            char_info = char_info_map.get(char, {'is_polyphone': False, 'all_zhuyin_options': []})

            # 決定使用哪個注音
            if char_info['is_polyphone']:
                # 多音字：優先使用 Gemini 的結果（根據上下文判斷）
                primary_zhuyin = gemini_zhuyin_map.get(f"{char}_{char_index}", '')
                if not primary_zhuyin and char_info['all_zhuyin_options']:
                    primary_zhuyin = char_info['all_zhuyin_options'][0]
            else:
                # 非多音字：直接使用資料庫的注音
                if char_info['all_zhuyin_options']:
                    primary_zhuyin = char_info['all_zhuyin_options'][0]
                else:
                    # 資料庫沒有資料時，嘗試使用 Gemini 的結果
                    primary_zhuyin = gemini_zhuyin_map.get(f"{char}_{char_index}", '')

            char_index += 1

            result_item = {
                'character': char,
                'char_type': 'chinese',
                'primary_zhuyin': primary_zhuyin,
                'is_polyphone': char_info['is_polyphone'],
                'all_zhuyin_options': char_info['all_zhuyin_options']
            }

            if include_braille and primary_zhuyin:
                braille_result = self.braille_service.zhuyin_to_braille(primary_zhuyin)
                if braille_result:
                    result_item['braille'] = braille_result
                    result_item['braille_count'] = len(braille_result['symbols'])

            results.append(result_item)

        return results

    # ============================================================
    # 各類型轉換方法
    # ============================================================

    def _convert_number(self, number_str, include_braille=False):
        """
        轉換數字

        Args:
            number_str: 數字字串（可能包含全形數字）
            include_braille: 是否包含點字

        Returns:
            dict: 轉換結果
        """
        # 將全形數字轉換為半形
        normalized_number = ''
        for char in number_str:
            if char in self.FULLWIDTH_DIGITS:
                normalized_number += self.FULLWIDTH_DIGITS[char]
            else:
                normalized_number += char

        result_item = {
            'character': number_str,  # 保留原始字元顯示
            'char_type': 'number',
            'primary_zhuyin': '',  # 數字沒有注音
            'is_polyphone': False,
            'all_zhuyin_options': []
        }

        if include_braille:
            # 使用正規化後的數字進行點字轉換
            braille_result = self.braille_service.digit_to_braille(normalized_number)
            if braille_result:
                result_item['braille'] = braille_result
                result_item['braille_count'] = len(braille_result['symbols'])

        return result_item

    def _convert_english(self, english_str, include_braille=False):
        """
        轉換英文

        Args:
            english_str: 英文字串
            include_braille: 是否包含點字

        Returns:
            dict: 轉換結果
        """
        result_item = {
            'character': english_str,
            'char_type': 'english',
            'primary_zhuyin': '',  # 英文沒有注音
            'is_polyphone': False,
            'all_zhuyin_options': []
        }

        if include_braille:
            braille_result = self.braille_service.english_to_braille(english_str)
            if braille_result:
                result_item['braille'] = braille_result
                result_item['braille_count'] = len(braille_result['symbols'])

        return result_item

    def _convert_punctuation(self, punct, include_braille=False):
        """
        轉換標點符號

        Args:
            punct: 標點符號
            include_braille: 是否包含點字

        Returns:
            dict: 轉換結果
        """
        # 判斷是中文還是英文標點
        char_type = 'chinese_punct' if punct in self.CHINESE_PUNCTS else 'english_punct'

        result_item = {
            'character': punct,
            'char_type': char_type,
            'primary_zhuyin': '',  # 標點沒有注音
            'is_polyphone': False,
            'all_zhuyin_options': []
        }

        if include_braille:
            braille_result = self.braille_service.punctuation_to_braille(punct)
            if braille_result:
                result_item['braille'] = braille_result
                result_item['braille_count'] = len(braille_result['symbols'])

        return result_item

    # ============================================================
    # 輔助方法
    # ============================================================

    def _batch_get_char_info(self, chars):
        """批次查詢多個字的注音資訊（優化效能）"""
        if not chars:
            return {}

        unique_chars = list(set(chars))

        result_map = {}
        chars_to_query = []

        for char in unique_chars:
            if char in self._cache:
                result_map[char] = self._cache[char]
            else:
                chars_to_query.append(char)

        if not chars_to_query:
            return result_map

        try:
            unicode_to_char = {f"{ord(char):04X}": char for char in chars_to_query}
            unicode_codes = list(unicode_to_char.keys())

            connection = get_db_connection()

            with connection.cursor() as cursor:
                placeholders = ','.join(['%s'] * len(unicode_codes))
                query = f"SELECT unicode_code, hanzi, bpmf, quantity FROM zhuyin WHERE unicode_code IN ({placeholders})"
                cursor.execute(query, unicode_codes)
                rows = cursor.fetchall()

            connection.close()

            found_chars = set()
            for row in rows:
                char = unicode_to_char.get(row['unicode_code'])
                if char and row['bpmf']:
                    bpmf_list = [b.strip() for b in row['bpmf'].split(';') if b.strip()]
                    is_polyphone = row['quantity'] > 1
                    char_info = {
                        'is_polyphone': is_polyphone,
                        'all_zhuyin_options': bpmf_list
                    }
                    result_map[char] = char_info
                    self._cache[char] = char_info
                    found_chars.add(char)

            missing_chars = [c for c in chars_to_query if c not in found_chars]
            if missing_chars:
                connection = get_db_connection()
                with connection.cursor() as cursor:
                    placeholders = ','.join(['%s'] * len(missing_chars))
                    query = f"SELECT hanzi, bpmf, quantity FROM zhuyin WHERE hanzi IN ({placeholders}) AND quantity > 0"
                    cursor.execute(query, missing_chars)
                    rows = cursor.fetchall()
                connection.close()

                for row in rows:
                    char = row['hanzi']
                    if char and row['bpmf']:
                        bpmf_list = [b.strip() for b in row['bpmf'].split(';') if b.strip()]
                        is_polyphone = row['quantity'] > 1
                        char_info = {
                            'is_polyphone': is_polyphone,
                            'all_zhuyin_options': bpmf_list
                        }
                        result_map[char] = char_info
                        self._cache[char] = char_info

            for char in chars_to_query:
                if char not in result_map:
                    default_info = {'is_polyphone': False, 'all_zhuyin_options': []}
                    result_map[char] = default_info
                    self._cache[char] = default_info

            return result_map

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {char: {'is_polyphone': False, 'all_zhuyin_options': []} for char in chars_to_query}

    def _is_chinese_char(self, char):
        """判斷是否為中文字"""
        return '\u4e00' <= char <= '\u9fff'

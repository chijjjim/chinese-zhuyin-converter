"""
點字轉換服務
將注音符號、英文、數字、標點符號轉換為點字（盲文）
"""

import os
import csv
from database.db import get_db_connection

class BrailleService:
    """點字轉換服務"""

    # ============================================================
    # 注音相關常數
    # ============================================================

    # 聲母列表
    INITIALS = ['ㄅ', 'ㄆ', 'ㄇ', 'ㄈ', 'ㄉ', 'ㄊ', 'ㄋ', 'ㄌ',
                'ㄍ', 'ㄎ', 'ㄏ', 'ㄐ', 'ㄑ', 'ㄒ',
                'ㄓ', 'ㄔ', 'ㄕ', 'ㄖ', 'ㄗ', 'ㄘ', 'ㄙ']

    # 需要加 ㄦ 的聲母（單獨成字時）
    INITIALS_NEED_ER = ['ㄓ', 'ㄔ', 'ㄕ', 'ㄖ', 'ㄗ', 'ㄘ', 'ㄙ']

    # 韻母列表
    FINALS = ['ㄚ', 'ㄛ', 'ㄜ', 'ㄝ', 'ㄞ', 'ㄟ', 'ㄠ', 'ㄡ',
              'ㄢ', 'ㄣ', 'ㄤ', 'ㄥ', 'ㄦ']

    # 介母列表
    MEDIALS = ['ㄧ', 'ㄨ', 'ㄩ']

    # 結合韻列表（按長度排序，優先匹配較長的）
    COMPOUND_FINALS = [
        'ㄧㄚ', 'ㄧㄛ', 'ㄧㄝ', 'ㄧㄞ', 'ㄧㄠ', 'ㄧㄡ', 'ㄧㄢ', 'ㄧㄣ', 'ㄧㄤ', 'ㄧㄥ',
        'ㄨㄚ', 'ㄨㄛ', 'ㄨㄞ', 'ㄨㄟ', 'ㄨㄢ', 'ㄨㄣ', 'ㄨㄤ', 'ㄨㄥ',
        'ㄩㄝ', 'ㄩㄢ', 'ㄩㄣ', 'ㄩㄥ'
    ]

    # 聲調列表
    TONES = ['ˊ', 'ˇ', 'ˋ', '˙']

    # ============================================================
    # 數字相關常數
    # ============================================================

    DIGITS = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    NUMBER_PREFIX = '⠼'  # 數符

    # ============================================================
    # 英文相關常數
    # ============================================================

    ENGLISH_LETTERS = list('abcdefghijklmnopqrstuvwxyz')
    CAPITAL_PREFIX = '⠠'  # 大寫符號

    def __init__(self, use_mysql=True):
        """初始化點字服務"""
        self.braille_map = {}
        self.abbreviation_map = {}  # 縮寫詞對照表
        self.use_mysql = use_mysql

        if use_mysql:
            try:
                self._load_braille_from_db()
            except Exception as e:
                self._load_braille_from_csv()
        else:
            self._load_braille_from_csv()

    def _load_braille_from_db(self):
        """從 MySQL 載入點字對照表"""
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT bpmf, braille_char, unicode_code, n_value, e_value, bpmf_type
                    FROM braille
                """)
                rows = cursor.fetchall()

                for row in rows:
                    bpmf = row['bpmf']
                    bpmf_type = row['bpmf_type']

                    info = {
                        'braille': row['braille_char'],
                        'unicode': row['unicode_code'] if row['unicode_code'] else '',
                        'n_value': str(row['n_value']) if row['n_value'] else '',
                        'e_value': row['e_value'] if row['e_value'] else '',
                        'type': bpmf_type
                    }

                    self.braille_map[bpmf] = info

                    # 縮寫詞另外存一份（用於最長匹配）
                    if bpmf_type == 'abbreviation':
                        self.abbreviation_map[bpmf.lower()] = info

        finally:
            connection.close()

    def _load_braille_from_csv(self):
        """從 CSV 載入點字對照表（備用方案）"""
        csv_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'scripts', 'braille.csv'
        )

        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    bpmf = row['bpmf'].strip()
                    if bpmf:
                        self.braille_map[bpmf] = {
                            'braille': row['braille'].strip(),
                            'unicode': row['Unicode'].strip(),
                            'n_value': row['n_value'].strip(),
                            'e_value': row['e_value'].strip()
                        }
        except Exception as e:
            raise

    # ============================================================
    # 注音轉點字
    # ============================================================

    def zhuyin_to_braille(self, zhuyin):
        """
        將注音轉換為點字

        Args:
            zhuyin: 注音字串，如 'ㄋㄧㄣˊ'

        Returns:
            dict: 包含點字符號和相關資訊
        """
        if not zhuyin:
            return None

        # 拆解注音
        parts = self._parse_zhuyin(zhuyin)

        if not parts:
            return None

        # 組合點字
        braille_symbols = ''
        braille_parts = []
        e_values = []
        n_values = []

        for part in parts:
            zhuyin_part = part['zhuyin']
            part_type = part['type']

            if zhuyin_part in self.braille_map:
                info = self.braille_map[zhuyin_part]
                braille_symbols += info['braille']
                e_values.append(info['e_value'])
                n_values.append(info['n_value'])
                braille_parts.append({
                    'zhuyin': zhuyin_part,
                    'braille': info['braille'],
                    'type': part_type,
                    'e_value': info['e_value'],
                    'n_value': info['n_value']
                })
            elif zhuyin_part == '一聲':
                # 一聲的特殊處理
                info = self.braille_map.get('一聲', {'braille': '⠄', 'e_value': "'", 'n_value': '4'})
                braille_symbols += info['braille']
                e_values.append(info['e_value'])
                n_values.append(info['n_value'])
                braille_parts.append({
                    'zhuyin': '一聲',
                    'braille': info['braille'],
                    'type': '聲調',
                    'e_value': info['e_value'],
                    'n_value': info['n_value']
                })

        return {
            'symbols': braille_symbols,
            'parts': braille_parts,
            'e_value': ''.join(e_values),
            'n_value': ' '.join(n_values)
        }

    def _parse_zhuyin(self, zhuyin):
        """
        拆解注音符號

        規則：
        1. 每個字最多3個點字（聲母 + 韻母/結合韻 + 聲調）
        2. ㄓㄔㄕㄖㄗㄘㄙ 單獨成字時後面要加 ㄦ
        3. 優先使用結合韻
        4. 輕聲 (˙) 在開頭時（如 ˙ㄉㄜ），點字聲調仍放在最後

        Args:
            zhuyin: 注音字串

        Returns:
            list: 拆解後的部分列表
        """
        parts = []
        remaining = zhuyin

        # 特殊處理：輕聲在開頭 (˙ㄉㄜ)
        has_leading_neutral_tone = False
        if remaining.startswith('˙'):
            has_leading_neutral_tone = True
            remaining = remaining[1:]  # 移除開頭的 ˙

        # 1. 提取聲調（排除已處理的輕聲）
        tone = None
        if not has_leading_neutral_tone:
            for t in self.TONES:
                if t in remaining:
                    tone = t
                    remaining = remaining.replace(t, '')
                    break

        # 2. 提取聲母
        initial = None
        if remaining and remaining[0] in self.INITIALS:
            initial = remaining[0]
            remaining = remaining[1:]

        # 3. 處理韻母部分
        final_part = None

        # 優先檢查結合韻
        for cf in self.COMPOUND_FINALS:
            if remaining == cf or remaining.startswith(cf):
                final_part = cf
                remaining = remaining[len(cf):]
                break

        # 如果沒有結合韻，檢查介母+韻母
        if not final_part and remaining:
            # 檢查是否只有介母（如 ㄧ、ㄨ、ㄩ）
            if remaining in self.MEDIALS:
                final_part = remaining
                remaining = ''
            # 檢查介母+韻母的組合
            elif len(remaining) >= 2 and remaining[0] in self.MEDIALS:
                # 嘗試匹配結合韻
                possible_compound = remaining[:2]
                if possible_compound in self.COMPOUND_FINALS:
                    final_part = possible_compound
                    remaining = remaining[2:]
                else:
                    # 分開處理介母和韻母
                    final_part = remaining
                    remaining = ''
            elif remaining[0] in self.FINALS:
                final_part = remaining[0]
                remaining = remaining[1:]
            else:
                # 剩餘的都當作韻母
                final_part = remaining
                remaining = ''

        # 4. 組合結果
        if initial:
            parts.append({'zhuyin': initial, 'type': '聲母'})

        # 判斷是否需要加 ㄦ
        # 規則：ㄓㄔㄕㄖㄗㄘㄙ 單獨成字時（只有聲母沒有韻母）要加 ㄦ
        if initial in self.INITIALS_NEED_ER and not final_part:
            parts.append({'zhuyin': 'ㄦ', 'type': '韻母'})
        elif final_part:
            # 判斷是結合韻還是單純韻母
            if final_part in self.COMPOUND_FINALS:
                parts.append({'zhuyin': final_part, 'type': '結合韻'})
            elif final_part in self.MEDIALS:
                parts.append({'zhuyin': final_part, 'type': '介母'})
            else:
                parts.append({'zhuyin': final_part, 'type': '韻母'})

        # 5. 加入聲調（輕聲移到最後，符合點字規則）
        if has_leading_neutral_tone:
            # 輕聲移到最後（點字規則）
            parts.append({'zhuyin': '˙', 'type': '聲調'})
        elif tone:
            parts.append({'zhuyin': tone, 'type': '聲調'})
        else:
            # 沒有聲調符號表示一聲
            parts.append({'zhuyin': '一聲', 'type': '聲調'})

        return parts

    # ============================================================
    # 數字轉點字
    # ============================================================

    def digit_to_braille(self, digit_sequence):
        """
        將數字序列轉換為點字

        規則：連續數字前加數符 ⠼（只需加一次）

        Args:
            digit_sequence: 數字字串，如 '123'

        Returns:
            dict: 包含點字符號和相關資訊
        """
        if not digit_sequence:
            return None

        braille_symbols = self.NUMBER_PREFIX  # 數符
        braille_parts = [{
            'original': '數符',
            'braille': self.NUMBER_PREFIX,
            'type': 'number_prefix'
        }]
        e_values = ['#']  # 數符的 e_value

        for digit in digit_sequence:
            if digit in self.braille_map:
                info = self.braille_map[digit]
                braille_symbols += info['braille']
                braille_parts.append({
                    'original': digit,
                    'braille': info['braille'],
                    'type': 'digit',
                    'e_value': info.get('e_value', '')
                })
                e_values.append(info.get('e_value', ''))

        return {
            'symbols': braille_symbols,
            'parts': braille_parts,
            'e_value': ''.join(e_values),
            'char_type': 'number'
        }

    # ============================================================
    # 英文轉點字
    # ============================================================

    def english_to_braille(self, text):
        """
        將英文文字轉換為點字

        規則：
        1. 大寫字母前需加大寫符號 ⠠
        2. 優先匹配縮寫詞（最長匹配）

        Args:
            text: 英文字串，如 'Hello'

        Returns:
            dict: 包含點字符號和相關資訊
        """
        if not text:
            return None

        braille_symbols = ''
        braille_parts = []
        e_values = []
        i = 0

        while i < len(text):
            # 嘗試最長縮寫詞匹配
            matched_abbr = self._match_abbreviation(text[i:])

            if matched_abbr:
                abbr_info = self.abbreviation_map[matched_abbr.lower()]
                braille_symbols += abbr_info['braille']
                braille_parts.append({
                    'original': matched_abbr,
                    'braille': abbr_info['braille'],
                    'type': 'abbreviation',
                    'e_value': abbr_info.get('e_value', '')
                })
                e_values.append(abbr_info.get('e_value', ''))
                i += len(matched_abbr)
            else:
                char = text[i]
                # 判斷是否為大寫
                if char.isupper():
                    # 加大寫符號
                    braille_symbols += self.CAPITAL_PREFIX
                    braille_parts.append({
                        'original': '大寫符號',
                        'braille': self.CAPITAL_PREFIX,
                        'type': 'capital_prefix'
                    })
                    e_values.append(',')  # 大寫符號的 e_value

                # 取得字母對應的點字（用小寫查詢）
                lower_char = char.lower()
                if lower_char in self.braille_map:
                    info = self.braille_map[lower_char]
                    braille_symbols += info['braille']
                    braille_parts.append({
                        'original': char,
                        'braille': info['braille'],
                        'type': 'english',
                        'e_value': info.get('e_value', '')
                    })
                    e_values.append(info.get('e_value', ''))

                i += 1

        return {
            'symbols': braille_symbols,
            'parts': braille_parts,
            'e_value': ''.join(e_values),
            'char_type': 'english'
        }

    def _match_abbreviation(self, text):
        """
        最長縮寫詞匹配

        Args:
            text: 要匹配的文字

        Returns:
            str: 匹配到的縮寫詞，或 None
        """
        if not text:
            return None

        text_lower = text.lower()
        matched = None
        max_len = 0

        # 從縮寫詞表中找最長匹配
        for abbr in self.abbreviation_map.keys():
            if text_lower.startswith(abbr) and len(abbr) > max_len:
                # 確保是完整單字匹配（後面是空格、標點或結尾）
                next_pos = len(abbr)
                if next_pos >= len(text) or not text[next_pos].isalpha():
                    matched = text[:len(abbr)]  # 保留原始大小寫
                    max_len = len(abbr)

        return matched

    def _is_english_char(self, char):
        """判斷是否為英文字母"""
        return char.lower() in self.ENGLISH_LETTERS

    # ============================================================
    # 標點符號轉點字
    # ============================================================

    def punctuation_to_braille(self, char):
        """
        將標點符號轉換為點字

        Args:
            char: 標點符號

        Returns:
            dict: 包含點字符號和相關資訊
        """
        if not char:
            return None

        # 直接查表
        if char in self.braille_map:
            info = self.braille_map[char]
            return {
                'symbols': info['braille'],
                'parts': [{
                    'original': char,
                    'braille': info['braille'],
                    'type': info.get('type', 'punctuation'),
                    'e_value': info.get('e_value', '')
                }],
                'e_value': info.get('e_value', ''),
                'char_type': 'punctuation'
            }

        return None

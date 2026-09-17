from flask import Blueprint, request, jsonify
from services.conversion_service import ConversionService

# 建立 Blueprint
zhuyin_bp = Blueprint('zhuyin', __name__)

# 初始化轉換服務
conversion_service = ConversionService()

@zhuyin_bp.route('/convert', methods=['POST'])
def convert_text():
    try:
        # 取得請求資料
        data = request.get_json()

        # 驗證輸入
        if not data or 'text' not in data:
            return jsonify({
                'success': False,
                'error_message': '缺少 text 欄位'
            }), 400

        text = data['text'].strip()

        if not text:
            return jsonify({
                'success': False,
                'error_message': '文字不能為空'
            }), 400

        # 取得是否包含點字的參數（預設為 False）
        include_braille = data.get('include_braille', False)

        # 呼叫轉換服務
        result = conversion_service.convert_text(text, include_braille)

        # 回傳結果
        return jsonify(result), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error_message': f'伺服器錯誤: {str(e)}'
        }), 500

@zhuyin_bp.route('/braille', methods=['POST'])
def convert_to_braille():
    """將單一注音轉換為點字"""
    try:
        data = request.get_json()
        zhuyin = data.get('zhuyin', '').strip()

        if not zhuyin:
            return jsonify({
                'success': False,
                'error_message': '缺少 zhuyin 欄位'
            }), 400

        braille_result = conversion_service.braille_service.zhuyin_to_braille(zhuyin)

        if braille_result:
            return jsonify({
                'success': True,
                'braille': braille_result,
                'braille_count': len(braille_result['symbols'])
            }), 200
        else:
            return jsonify({
                'success': False,
                'error_message': f'無法轉換注音: {zhuyin}'
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'error_message': str(e)
        }), 500


@zhuyin_bp.route('/health', methods=['GET'])
def health_check():
    """健康檢查 API"""
    return jsonify({
        'status': 'ok',
        'message': '注音轉換服務運行中'
    }), 200

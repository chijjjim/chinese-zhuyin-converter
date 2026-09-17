from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from routes.zhuyin_routes import zhuyin_bp

def create_app():
    """建立 Flask 應用程式"""
    
    # 初始化 Flask
    app = Flask(__name__,
                static_folder='../frontend',
                static_url_path='')    
    # 載入配置
    app.config.from_object(Config)
    
    # 啟用 CORS（允許前端跨域請求）
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://140.128.10.26"],
            "methods": ["GET", "POST", "PUT", "DELETE"],
            "allow_headers": ["Content-Type"]
        }
    })
    
    # 註冊 API 路由
    app.register_blueprint(zhuyin_bp, url_prefix='/api')
    
    # 根路由
    @app.route('/')
    def index():
        return app.send_static_file('bpmf.php')
    
    # 錯誤處理
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error_message': '找不到此 API 端點'
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'success': False,
            'error_message': '伺服器內部錯誤'
        }), 500
    
    return app
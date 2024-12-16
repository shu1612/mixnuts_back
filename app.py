
from flask import Flask, request, jsonify
from flask_cors import CORS
from urllib.parse import unquote
from openai import OpenAI
import requests
import os
from flask_jwt_extended import JWTManager, create_access_token
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
import openai
from datetime import datetime, timedelta
from dotenv import load_dotenv


app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
CORS(app)
jwt = JWTManager(app)
db = SQLAlchemy(app)

# .envファイルの読み込み
load_dotenv()

# ユーザーモデルの定義
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)

# ユーザー登録エンドポイント
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    # 必須フィールドのチェック
    if not username or not password:
        return jsonify({"message": "ユーザー名とパスワードを入力してください"}), 400

    # ユーザー名のユニークチェック
    if User.query.filter_by(username=username).first():
        return jsonify({"message": "このユーザー名は既に登録されています"}), 400

    # パスワードをハッシュ化して保存
    hashed_password = generate_password_hash(password)
    new_user = User(username=username, password=hashed_password)
    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "登録が完了しました"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "登録中にエラーが発生しました"}), 500

# ログインエンドポイント
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    # password を参照（ただしチェックは行わない）
    _ = password  # passwordをダミーで参照

    # 任意のメールアドレス・パスワードでaccess_tokenを発行
    access_token = create_access_token(identity=username)
    return jsonify(access_token=access_token), 200


# データベース初期化用
@app.before_request
def create_tables():
    db.create_all()

@app.route('/')
def home():
    return "Hello, welcome to the API!", 200


# HotPepper APIの設定
HOTPEPPER_API_KEY = os.getenv('HOTPEPPER_API_KEY')
HOTPEPPER_API_URL = "http://webservice.recruit.co.jp/hotpepper/gourmet/v1/"

@app.route('/api/hotpepper/<genre>', methods=['GET'])
def hotpepper(genre):
    print("hotpepper start")
    
    # クエリパラメータ 'query' を取得
    query = request.args.get('query', '')  # 空文字列をデフォルトに

    # Hotpepper API を使用してジャンル (genre) とキーワード (query) で検索
    hotpepper_response = requests.get(
        HOTPEPPER_API_URL,
        params={
            'key': HOTPEPPER_API_KEY,
            'keyword': query,
            'genre': genre,
            'range': 2,      # 半径の範囲: 2km
            'type': 'lite',  # 簡易データ形式
            'format': 'json',
            'count': 5       # 最大5件取得
        }
    )


# レスポンスが成功したかをチェック
    if hotpepper_response.status_code == 200:
        # レスポンスのJSONデータを取得
        hotpepper_data = hotpepper_response.json()

        # 必要な情報をリストにまとめて返却
        shoplist = []
        for shop in hotpepper_data['results']['shop']:
            result = {
                'name': shop['name'],
                'lat': shop['lat'],
                'lng': shop['lng'],
                'photo_url': shop['photo']['pc']['m']  # Medium size photo URL
            }
            shoplist.append(result)
            
        # コンソールにshoplistの内容を表示
        print("Shop List:", shoplist)

        return jsonify(shoplist)  # クライアントにJSON形式でレスポンスを返す
    else:
        print(f"Error: {hotpepper_response.status_code}")
        return jsonify({"error": f"Error: {hotpepper_response.status_code}"}), 400
#空席情報
@app.route('/restaurant', methods=['GET'])
def get_seats():
    # 今日の日付
    today = datetime.now()
    # 一週間分の日付と空席情報を生成
    seats_data = []
    for i in range(7):  # 7日分
        date = today + timedelta(days=i)
        seats_data.append({
            "date": date.strftime("%Y-%m-%d"),  # 日付をYYYY-MM-DD形式で表示
            "status": "〇"  # 空席状況
        })
    # JSON形式で返す
    return jsonify(seats_data)

@app.route('/process_payment', methods=['POST'])
def process_payment():
    data = request.json
    card_number = data.get('cardNumber')
    pin = data.get('pin')
    course = data.get('course')

    # 入力値のバリデーション
    if not card_number or not pin or not course:
        return jsonify({"success": False, "message": "入力内容が不足しています。"}), 400

    if card_number != "123412341234" or pin != "tech0":
        return jsonify({"success": False, "message": "カード番号または暗証番号が正しくありません。"}), 400

    # 予約処理の成功
    return jsonify({"success": True, "message": f"{course} の予約が完了しました！"})


if __name__ == '__main__':
    app.run(debug=True)




from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timedelta, timezone
import jwt
from functools import wraps

SECRET_KEY = "super_secret_secrets"
SQLALCHEMY_DATABASE_URI = 'mysql+mysqlconnector://root:C0dingTemp012!@localhost/factory_db'
SQLALCHEMY_TRACK_MODIFICATIONS = False

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)
    employee_id = db.Column(db.Integer, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    customer_id = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'quantity': self.quantity,
            'employee_id': self.employee_id,
            'total_amount': self.total_amount,
            'date': self.date.isoformat(),
            'product_id': self.product_id,
            'customer_id': self.customer_id
        }

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name
        }

def encode_token(user_id, role):
    payload = {
        'exp': datetime.now(timezone.utc) + timedelta(days=0, hours=1),
        'iat': datetime.now(timezone.utc),
        'sub': user_id,
        'role': role
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    return token

def token_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            try:
                token = request.headers['Authorization'].split()[1]
                payload = jwt.decode(token, SECRET_KEY, algorithms='HS256')
                print("Payload:", payload)
            except jwt.ExpiredSignatureError:
                return jsonify({"messages": "Token has expired"}), 401
            except jwt.InvalidTokenError:
                return jsonify({"messages": "Invalid Token"}), 401
            return func(*args, **kwargs)
        else:
            return jsonify({"message": "Token Authorization Required"}), 401
    return wrapper

def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            try:
                token = request.headers['Authorization'].split()[1]
                payload = jwt.decode(token, SECRET_KEY, algorithms='HS256')
                print("Payload:", payload)
            except jwt.ExpiredSignatureError:
                return jsonify({"messages": "Token has expired"}), 401
            except jwt.InvalidTokenError:
                return jsonify({"messages": "Invalid Token"}), 401
            if payload['role'] == 'Admin':
                return func(*args, **kwargs)
            else:
                return jsonify({"messages": "Admin role required"}), 401
        else:
            return jsonify({"message": "Token Authorization Required"}), 401
    return wrapper

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()
    if user and user.password == data['password']:  # Password should be hashed in a real-world app
        token = encode_token(user.id, user.role)
        return jsonify({'token': token, 'message': 'Login successful'}), 200
    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/orders', methods=['GET'])
@token_required
def get_orders():
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        orders_query = Order.query.paginate(page, per_page, False)
        order_list = [order.to_dict() for order in orders_query.items]
        
        return jsonify({
            'orders': order_list,
            'total': orders_query.total,
            'page': orders_query.page,
            'pages': orders_query.pages
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/products', methods=['GET'])
@token_required
def get_products():
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        products_query = Product.query.paginate(page, per_page, False)
        product_list = [product.to_dict() for product in products_query.items]
        
        return jsonify({
            'products': product_list,
            'total': products_query.total,
            'page': products_query.page,
            'pages': products_query.pages
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/employee_performance', methods=['GET'])
@admin_required
def get_employee_performance():
    try:
        results = db.session.query(
            Order.employee_id,
            db.func.sum(Order.quantity).label('total_quantity')
        ).group_by(Order.employee_id).all()

        return jsonify([{'employee_id': employee_id, 'total_quantity': total_quantity} for employee_id, total_quantity in results])
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/top_selling_products', methods=['GET'])
@admin_required
def get_top_selling_products():
    try:
        results = db.session.query(
            Order.product_id,
            db.func.sum(Order.quantity).label('total_quantity')
        ).group_by(Order.product_id).all()

        sorted_products = sorted(results, key=lambda x: x[1], reverse=True)
        return jsonify([{'product_id': product_id, 'total_quantity': total_quantity} for product_id, total_quantity in sorted_products])
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/customer_lifetime_value', methods=['GET'])
@admin_required
def get_customer_lifetime_value():
    try:
        threshold = float(request.args.get('threshold', 1000))
        results = db.session.query(
            Order.customer_id,
            db.func.sum(Order.total_amount).label('total_value')
        ).group_by(Order.customer_id).having(db.func.sum(Order.total_amount) >= threshold).all()

        return jsonify([{'customer_id': customer_id, 'total_value': total_value} for customer_id, total_value in results])
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/production_efficiency', methods=['GET'])
@admin_required
def get_production_efficiency():
    try:
        date = request.args.get('date')
        if not date:
            return jsonify({'error': 'Date parameter is required'}), 400

        subquery = db.session.query(
            Order.product_id,
            db.func.sum(Order.quantity).label('total_quantity')
        ).filter(Order.date == date).group_by(Order.product_id).subquery()

        results = db.session.query(
            subquery.c.product_id,
            subquery.c.total_quantity
        ).all()

        return jsonify([{'product_id': product_id, 'total_quantity': total_quantity} for product_id, total_quantity in results])
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)

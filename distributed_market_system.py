from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Api, Resource
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_
from functools import wraps
import traceback
import os
from flask import Flask
import sys


base_dir = os.path.dirname(os.path.abspath(__file__))
template_path = os.path.join(base_dir, 'templates')
app = Flask(__name__, template_folder=template_path)
app.secret_key = 'your_secret_key_here'  # Replace with a secure key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///market.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
api = Api(app)

if getattr(sys, 'frozen', False):
    # Running as bundled exe
    base_path = sys._MEIPASS
else:
    base_path = os.path.abspath(".")

db_path = os.path.join(base_path, "market.db")
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
# Models

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    items = db.relationship('Item', backref='owner', lazy=True)
    purchases = db.relationship('Transaction', foreign_keys='Transaction.buyer_id', backref='buyer', lazy=True)
    sales = db.relationship('Transaction', foreign_keys='Transaction.seller_id', backref='seller', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    price = db.Column(db.Float, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    for_sale = db.Column(db.Boolean, default=True)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    price = db.Column(db.Float, nullable=False)

    item = db.relationship('Item')

@app.before_request
def create_tables_and_db():
    db_file = os.path.join(base_path, 'market.db')
    if not os.path.exists(db_file):
        open(db_file, 'a').close()  # Create empty file if missing
    db.create_all()

# Helpers

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def get_json_data():
    if not request.is_json:
        return None, jsonify({"error": "Invalid or missing JSON in request"}), 400
    return request.get_json(), None, None

# Frontend routes

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login_page'))

@app.route('/login')
def login_page():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', username=session.get('username'))

# API Resources

class RegisterResource(Resource):
    def post(self):
        data, err_response, code = get_json_data()
        if err_response:
            return err_response, code
        username = data.get('username')
        password = data.get('password')
        if not username or not password:
            return {"error": "Username and password required"}, 400
        if User.query.filter_by(username=username).first():
            return {"error": "Username already exists"}, 400
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        try:
            db.session.commit()
            return {"message": f"User '{username}' created successfully"}, 201
        except IntegrityError:
            db.session.rollback()
            return {"error": "Failed to create user"}, 500

class LoginResource(Resource):
    def post(self):
        data, err_response, code = get_json_data()
        if err_response:
            return err_response, code
        username = data.get('username')
        password = data.get('password')
        if not username or not password:
            return {"error": "Username and password required"}, 400
        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            return {"error": "Invalid username or password"}, 401
        # Set session info
        session['user_id'] = user.id
        session['username'] = user.username
        return {"message": "Login successful", "user_id": user.id, "username": user.username}

class ItemResource(Resource):
    def post(self):
        data, err_response, code = get_json_data()
        if err_response:
            return err_response, code
        user_id = data.get('owner_id')
        name = data.get('name')
        price = data.get('price')
        if not all([user_id, name, price]):
            return {"error": "owner_id, name, and price are required"}, 400
        user = User.query.get(user_id)
        if not user:
            return {"error": "User not found"}, 404
        item = Item(name=name, price=price, owner_id=user_id, for_sale=True)
        db.session.add(item)
        db.session.commit()
        return {"message": f"Item '{name}' added for sale"}, 201

    def put(self):
        data, err_response, code = get_json_data()
        if err_response:
            return err_response, code
        item_id = data.get('item_id')
        user_id = data.get('owner_id')
        name = data.get('name')
        price = data.get('price')
        for_sale = data.get('for_sale', True)
        if not item_id or not user_id:
            return {"error": "item_id and owner_id required"}, 400
        item = Item.query.filter(and_(Item.id==item_id, Item.owner_id==user_id)).first()
        if not item:
            return {"error": "Item not found or you are not the owner"}, 404
        if name:
            item.name = name
        if price is not None:
            item.price = price
        item.for_sale = for_sale
        db.session.commit()
        return {"message": f"Item '{item.name}' updated"}, 200

    def delete(self):
        data, err_response, code = get_json_data()
        if err_response:
            return err_response, code
        item_id = data.get('item_id')
        user_id = data.get('owner_id')
        if not item_id or not user_id:
            return {"error": "item_id and owner_id required"}, 400
        item = Item.query.filter(and_(Item.id==item_id, Item.owner_id==user_id)).first()
        if not item:
            return {"error": "Item not found or you are not the owner"}, 404
        db.session.delete(item)
        db.session.commit()
        return {"message": "Item deleted"}, 200

class Deposit(Resource):
    def post(self):
        data, err_response, code = get_json_data()
        if err_response:
            return err_response, code
        user_id = data.get('user_id')
        amount = data.get('amount')
        if not user_id or amount is None:
            return {"error": "user_id and amount required"}, 400
        if amount <= 0:
            return {"error": "Deposit amount must be positive"}, 400
        user = User.query.get(user_id)
        if not user:
            return {"error": "User not found"}, 404
        user.balance += amount
        db.session.commit()
        return {"message": f"Deposited ${amount:.2f} to account", "new_balance": user.balance}

class Withdraw(Resource):
    def post(self):
        data, err_response, code = get_json_data()
        if err_response:
            return err_response, code
        user_id = data.get('user_id')
        amount = data.get('amount')
        if not user_id or amount is None:
            return {"error": "user_id and amount required"}, 400
        if amount <= 0:
            return {"error": "Withdraw amount must be positive"}, 400
        user = User.query.get(user_id)
        if not user:
            return {"error": "User not found"}, 404
        if user.balance < amount:
            return {"error": "Insufficient funds"}, 400
        user.balance -= amount
        db.session.commit()
        return {"message": f"Withdrew ${amount:.2f} from account", "new_balance": user.balance}

class SearchItems(Resource):
    def get(self):
        query = request.args.get('query', '')
        items = Item.query.filter(Item.for_sale==True).filter(Item.name.ilike(f'%{query}%')).all()
        result = []
        for item in items:
            result.append({
                "item_id": item.id,
                "name": item.name,
                "price": item.price,
                "owner_id": item.owner_id,
                "owner_username": item.owner.username
            })
        return {"items": result}

class Purchase(Resource):
    def post(self):
        data, err_response, code = get_json_data()
        if err_response:
            return err_response, code
        buyer_id = data.get('buyer_id')
        item_id = data.get('item_id')
        if not buyer_id or not item_id:
            return {"error": "buyer_id and item_id required"}, 400
        buyer = User.query.get(buyer_id)
        item = Item.query.get(item_id)
        if not buyer or not item or not item.for_sale:
            return {"error": "Buyer or item not found, or item not for sale"}, 404
        if buyer.balance < item.price:
            return {"error": "Insufficient balance"}, 400
        if item.owner_id == buyer.id:
            return {"error": "Cannot buy your own item"}, 400
        seller = User.query.get(item.owner_id)
        try:
            buyer.balance -= item.price
            seller.balance += item.price
            item.owner_id = buyer.id
            item.for_sale = False
            transaction = Transaction(item_id=item.id, buyer_id=buyer.id, seller_id=seller.id, price=item.price)
            db.session.add(transaction)
            db.session.commit()
            return {"message": f"Item '{item.name}' purchased successfully"}
        except Exception as e:
            db.session.rollback()
            return {"error": "Transaction failed", "details": str(e)}, 500

class AccountInfo(Resource):
    def get(self):
        user_id = request.args.get('user_id', type=int)
        if not user_id:
            return {"error": "user_id parameter is required"}, 400
        user = User.query.get(user_id)
        if not user:
            return {"error": "User not found"}, 404
        purchased_items = []
        for txn in user.purchases:
            purchased_items.append({
                "item_id": txn.item.id,
                "name": txn.item.name,
                "price": txn.price,
                "seller": txn.seller.username
            })
        sold_items = []
        for txn in user.sales:
            sold_items.append({
                "item_id": txn.item.id,
                "name": txn.item.name,
                "price": txn.price,
                "buyer": txn.buyer.username
            })
        items_for_sale = []
        for item in user.items:
            if item.for_sale:
                items_for_sale.append({"item_id": item.id, "name": item.name, "price": item.price})
        return {
            "username": user.username,
            "balance": user.balance,
            "purchased_items": purchased_items,
            "sold_items": sold_items,
            "items_for_sale": items_for_sale
        }

class TransactionReport(Resource):
    def get(self):
        user_id = request.args.get('user_id', type=int)
        if not user_id:
            return {"error": "user_id parameter is required"}, 400
        user = User.query.get(user_id)
        if not user:
            return {"error": "User not found"}, 404
        transactions = Transaction.query.filter(
            (Transaction.buyer_id == user_id) | (Transaction.seller_id == user_id)
        ).all()
        report = []
        for txn in transactions:
            report.append({
                "transaction_id": txn.id,
                "item_name": txn.item.name,
                "price": txn.price,
                "buyer": txn.buyer.username,
                "seller": txn.seller.username
            })
        return {"transactions": report}

@app.errorhandler(500)
def internal_error(exception):
    tb = traceback.format_exc()
    app.logger.error(tb)
    return f"<pre>{tb}</pre>", 500

# API routing
api.add_resource(RegisterResource, '/api/register')
api.add_resource(LoginResource, '/api/login')
api.add_resource(ItemResource, '/api/items')
api.add_resource(Deposit, '/api/deposit')
api.add_resource(Withdraw, '/api/withdraw')
api.add_resource(SearchItems, '/api/search')
api.add_resource(Purchase, '/api/purchase')
api.add_resource(AccountInfo, '/api/account')
api.add_resource(TransactionReport, '/api/report')

if __name__ == '__main__':
    app.run(debug=True)

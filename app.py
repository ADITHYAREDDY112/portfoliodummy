from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your_very_secret_key"

# Functions
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def create_users_table():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')


def create_stocks_table():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS stocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                shares INTEGER NOT NULL,
                purchase_price REAL NOT NULL,
                purchase_date TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

def create_transactions_table():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                stock_id INTEGER,
                shares INTEGER NOT NULL,
                sell_price REAL NOT NULL,
                sell_date TEXT NOT NULL,
                profit_loss REAL NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (stock_id) REFERENCES stocks(id)
            )
        ''')

# Initialize tables
create_users_table()
create_stocks_table()
create_transactions_table()

@app.route('/')
def home():
    portfolio_exists = False  
    if 'user_id' in session:
        with get_db_connection() as conn:
            stock_count = conn.execute(
                "SELECT COUNT(*) FROM stocks WHERE user_id = ?", 
                (session['user_id'],)
            ).fetchone()[0]
            portfolio_exists = stock_count > 0  

    return render_template('index.html', portfolio=portfolio_exists)

@app.route('/add_stock', methods=['GET', 'POST'])
def add_stock():
    if 'user_id' not in session:
        return redirect(url_for('login'))  

    if request.method == 'POST':
        name = request.form.get('stock_name')
        shares = request.form.get('shares')
        purchase_price = request.form.get('price')
        purchase_date = request.form.get('purchase_date')

        if not name or not shares or not purchase_price or not purchase_date:
            return "All fields are required", 400  
        shares = int(shares)
        purchase_price = float(purchase_price)

        with get_db_connection() as conn:
            conn.execute('''
                INSERT INTO stocks (user_id, name, shares, purchase_price, purchase_date) 
                VALUES (?, ?, ?, ?, ?)
            ''', (session['user_id'], name, shares, purchase_price, purchase_date))
            conn.commit()

        return redirect(url_for('portfolio')) 

    return render_template('add_stock.html')





@app.route('/portfolio')
def portfolio():
    if 'user_id' not in session:
        return redirect(url_for('login'))  

    conn = get_db_connection()
    cursor = conn.cursor()
    
    user_id = session['user_id']
    cursor.execute("SELECT id, name, shares, purchase_price, purchase_date FROM stocks WHERE user_id = ?", (user_id,))
    stocks = [dict(stock) for stock in cursor.fetchall()]

    total_value = sum(stock['shares'] * stock['purchase_price'] for stock in stocks) if stocks else 0

    conn.close()
    
    return render_template('portfolio.html', stocks=stocks, total_value=total_value)

@app.route('/sell_stock/<stock_id>', methods=['POST'])
def sell_stock(stock_id):
    if 'user_id' not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    user_id = session['user_id']
    try:
        shares_to_sell = int(request.form['shares'])
        sell_price = float(request.form['sell_price'])
    except (ValueError, KeyError):
        return jsonify({"success": False, "error": "Invalid input"}), 400

    sell_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_db_connection() as conn:
        stock = conn.execute("SELECT * FROM stocks WHERE id = ? AND user_id = ?", (stock_id, user_id)).fetchone()
        if not stock or shares_to_sell > stock['shares']:
            return jsonify({"success": False, "error": "Invalid transaction"}), 400
        
        profit_loss = shares_to_sell * (sell_price - stock['purchase_price'])

        
        conn.execute('''
            INSERT INTO transactions (user_id, stock_id, shares, sell_price, sell_date, profit_loss)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, stock_id, shares_to_sell, sell_price, sell_date, profit_loss))

        
        if shares_to_sell == stock['shares']:
            conn.execute("DELETE FROM stocks WHERE id = ? AND user_id = ?", (stock_id, user_id))
        else:
            conn.execute("UPDATE stocks SET shares = shares - ? WHERE id = ? AND user_id = ?", (shares_to_sell, stock_id, user_id))
        
        conn.commit()

    return jsonify({"success": True, "profit_loss": profit_loss})




@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        with get_db_connection() as conn:
            user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                return redirect(url_for('home'))  
        return "Invalid username or password", 401

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        with get_db_connection() as conn:
            try:
                conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
                conn.commit()
                return redirect(url_for('home'))
            except sqlite3.IntegrityError:
                return render_template('register.html', error="Username already exists.")

    return render_template('register.html')




@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

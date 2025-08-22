"""
Web-based Budget App using Flask
Modern web UI with left-side navigation menu
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import os
import tempfile
from logic import BudgetLogic
from auto_classify import AutoClassificationEngine
import pandas as pd
from werkzeug.utils import secure_filename
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-change-this-in-production')

# Global logic instance
logic = None

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_logic():
    """Initialize database connection"""
    global logic
    if not logic:
        try:
            logic = BudgetLogic()  # Uses environment variables for connection
            return True
        except Exception as e:
            print(f"Failed to initialize database: {e}")
            return False
    return True

@app.route('/')
def index():
    if not init_logic():
        flash('Database connection failed', 'error')
        return render_template('error.html', message='Unable to connect to database')
    return render_template('dashboard.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    # PostgreSQL doesn't need login - just verify connection
    if init_logic():
        session['logged_in'] = True
        flash('Successfully connected to database!', 'success')
        return redirect(url_for('index'))
    else:
        flash('Unable to connect to database', 'error')
        return render_template('error.html', message='Database connection failed')

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import os
import tempfile
from logic import BudgetLogic
from auto_classify import AutoClassificationEngine
import pandas as pd
from werkzeug.utils import secure_filename
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'  # Change this in production

# Global logic instance (will be initialized after password entry)
logic = None

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    if not logic:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        db_path = request.form.get('db_path', 'budget.db')
        
        try:
            global logic
            logic = BudgetLogic(db_path, password)
            session['logged_in'] = True
            flash('Successfully logged in!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Login failed: {str(e)}', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    global logic
    if logic:
        logic.close()
        logic = None
    session.clear()
    flash('Logged out successfully', 'info')
    return redirect(url_for('login'))

@app.route('/budgets')
def budgets():
    if not logic:
        return redirect(url_for('login'))
    return render_template('budgets.html')

@app.route('/api/budgets/<int:year>')
def get_budgets(year):
    if not logic:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        budgets = logic.get_yearly_budgets(year)
        categories = logic.get_categories()
        
        budget_data = []
        for category in categories:
            budget_amount = budgets.get(category, 0.0)
            budget_data.append({
                'category': category,
                'yearly_budget': budget_amount
            })
        
        return jsonify({'budgets': budget_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/budgets/<int:year>', methods=['POST'])
def update_budget(year):
    if not logic:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        data = request.get_json()
        category = data.get('category')
        amount = float(data.get('amount', 0))
        
        logic.set_yearly_budget(category, year, amount)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories', methods=['POST'])
def add_category():
    if not logic:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        data = request.get_json()
        category_name = data.get('name', '').strip()
        
        if not category_name:
            return jsonify({'error': 'Category name required'}), 400
        
        logic.add_category(category_name)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories/<category_name>', methods=['DELETE'])
def delete_category(category_name):
    if not logic:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        logic.remove_category(category_name)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/import')
def import_csv():
    if not logic:
        return redirect(url_for('login'))
    return render_template('import.html')

@app.route('/api/import', methods=['POST'])
def upload_file():
    if not logic:
        return jsonify({'error': 'Not logged in'}), 401
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            count = logic.import_csv(filepath)
            # Clean up uploaded file
            os.remove(filepath)
            return jsonify({
                'success': True, 
                'message': f'Imported {count} transactions',
                'count': count
            })
        except Exception as e:
            # Clean up uploaded file on error
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/transactions')
def transactions():
    if not logic:
        return redirect(url_for('login'))
    return render_template('transactions.html')

@app.route('/api/transactions')
def get_transactions():
    if not logic:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        category_filter = request.args.get('category')
        
        transactions = logic.get_transactions(category=category_filter)
        
        # Simple pagination
        start = (page - 1) * per_page
        end = start + per_page
        paginated_transactions = transactions[start:end]
        
        # Format transactions for JSON
        formatted_transactions = []
        for tx in paginated_transactions:
            tx_id, verif_num, date, description, amount, category, year, month = tx
            formatted_transactions.append({
                'id': tx_id,
                'verifikationsnummer': verif_num,
                'date': date,
                'description': description,
                'amount': amount,
                'category': category,
                'year': year,
                'month': month
            })
        
        return jsonify({
            'transactions': formatted_transactions,
            'total': len(transactions),
            'page': page,
            'per_page': per_page,
            'has_more': end < len(transactions)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/uncategorized')
def uncategorized():
    if not logic:
        return redirect(url_for('login'))
    return render_template('uncategorized.html')

@app.route('/api/uncategorized')
def get_uncategorized():
    if not logic:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        
        transactions = logic.get_uncategorized_transactions()
        
        # Simple pagination
        start = (page - 1) * per_page
        end = start + per_page
        paginated_transactions = transactions[start:end]
        
        # Format transactions for JSON
        formatted_transactions = []
        for tx in paginated_transactions:
            tx_id, verif_num, date, description, amount, year, month = tx
            formatted_transactions.append({
                'id': tx_id,
                'verifikationsnummer': verif_num,
                'date': date,
                'description': description,
                'amount': amount,
                'year': year,
                'month': month
            })
        
        return jsonify({
            'transactions': formatted_transactions,
            'total': len(transactions),
            'page': page,
            'per_page': per_page,
            'has_more': end < len(transactions),
            'total_uncategorized': logic.get_uncategorized_count()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/classify', methods=['POST'])
def classify_transaction():
    if not logic:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        data = request.get_json()
        tx_id = data.get('transaction_id')
        category = data.get('category')
        
        if not tx_id or not category:
            return jsonify({'error': 'Transaction ID and category required'}), 400
        
        logic.reclassify_transaction(tx_id, category)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/classify/batch', methods=['POST'])
def batch_classify():
    if not logic:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        data = request.get_json()
        classifications = data.get('classifications', [])
        
        success_count = 0
        for item in classifications:
            tx_id = item.get('transaction_id')
            category = item.get('category')
            
            if tx_id and category:
                logic.reclassify_transaction(tx_id, category)
                success_count += 1
        
        return jsonify({
            'success': True, 
            'classified': success_count,
            'total': len(classifications)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auto-classify', methods=['POST'])
def auto_classify():
    if not logic:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        data = request.get_json()
        confidence_threshold = float(data.get('confidence_threshold', 0.8))
        
        engine = AutoClassificationEngine(logic)
        classified_count, suggestions = engine.auto_classify_uncategorized(confidence_threshold)
        
        return jsonify({
            'success': True,
            'classified': classified_count,
            'suggestions': len(suggestions),
            'remaining': logic.get_uncategorized_count()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/reports')
def reports():
    if not logic:
        return redirect(url_for('login'))
    return render_template('reports.html')

@app.route('/api/reports/monthly/<int:year>/<int:month>')
def monthly_report(year, month):
    if not logic:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        report_data = logic.generate_monthly_report(year, month)
        return jsonify({'report': report_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reports/yearly/<int:year>')
def yearly_report(year):
    if not logic:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        report_data = logic.generate_yearly_report(year)
        return jsonify({'report': report_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories')
def get_categories():
    if not logic:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        categories = logic.get_categories()
        return jsonify({'categories': categories})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

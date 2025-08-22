"""
Web-based Budget App using Flask
Modern web UI with left-side navigation menu and user authentication
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
from functools import wraps

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

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') or not session.get('username'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Please enter both username and password', 'error')
            return render_template('login.html')
        
        # Initialize database connection to check credentials
        if not init_logic():
            flash('Database connection failed', 'error')
            return render_template('login.html')
        
        # Authenticate user
        if logic.db.authenticate_user(username, password):
            session['logged_in'] = True
            session['username'] = username
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
            return render_template('login.html')
    
    # GET request - show login form
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    """Main dashboard page"""
    if not init_logic():
        flash('Database connection failed', 'error')
        return render_template('error.html', message='Database connection failed')
    
    try:
        # Get summary data for dashboard
        categories = logic.get_categories()
        transactions_count = len(logic.get_transactions())
        
        # Get recent transactions (last 10)
        recent_transactions = logic.get_transactions()[-10:] if logic.get_transactions() else []
        
        return render_template('dashboard.html', 
                             categories=categories,
                             transactions_count=transactions_count,
                             recent_transactions=recent_transactions,
                             current_user=session.get('username'))
    except Exception as e:
        flash(f'Error loading dashboard: {e}', 'error')
        return render_template('error.html', message=str(e))

@app.route('/transactions')
@login_required
def transactions():
    """Display all transactions"""
    if not init_logic():
        flash('Database connection failed', 'error')
        return render_template('error.html', message='Database connection failed')
    
    try:
        all_transactions = logic.get_transactions()
        categories = logic.get_categories()
        return render_template('transactions.html', 
                             transactions=all_transactions, 
                             categories=categories,
                             current_user=session.get('username'))
    except Exception as e:
        flash(f'Error loading transactions: {e}', 'error')
        return render_template('error.html', message=str(e))

@app.route('/budgets')
@login_required
def budgets():
    """Display budget management page"""
    if not init_logic():
        flash('Database connection failed', 'error')
        return render_template('error.html', message='Database connection failed')
    
    try:
        categories = logic.get_categories()
        budget_data = logic.get_budgets()  # Get all budget data
        return render_template('budgets.html', 
                             categories=categories,
                             budgets=budget_data,
                             current_user=session.get('username'))
    except Exception as e:
        flash(f'Error loading budgets: {e}', 'error')
        return render_template('error.html', message=str(e))

@app.route('/reports')
@login_required
def reports():
    """Display reports page"""
    if not init_logic():
        flash('Database connection failed', 'error')
        return render_template('error.html', message='Database connection failed')
    
    try:
        categories = logic.get_categories()
        return render_template('reports.html', 
                             categories=categories,
                             current_user=session.get('username'))
    except Exception as e:
        flash(f'Error loading reports: {e}', 'error')
        return render_template('error.html', message=str(e))

@app.route('/import_csv')
@login_required
def import_csv():
    """Display CSV import page"""
    return render_template('import.html', current_user=session.get('username'))

@app.route('/uncategorized')
@login_required
def uncategorized():
    """Display uncategorized transactions"""
    if not init_logic():
        flash('Database connection failed', 'error')
        return render_template('error.html', message='Database connection failed')
    
    try:
        uncategorized_transactions = logic.get_uncategorized_transactions()
        categories = logic.get_categories()
        return render_template('uncategorized.html', 
                             transactions=uncategorized_transactions,
                             categories=categories,
                             current_user=session.get('username'))
    except Exception as e:
        flash(f'Error loading uncategorized transactions: {e}', 'error')
        return render_template('error.html', message=str(e))

# API endpoints (all require login)
@app.route('/api/categorize_transaction', methods=['POST'])
@login_required
def categorize_transaction():
    """API endpoint to categorize a transaction"""
    if not init_logic():
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        data = request.get_json()
        transaction_id = data.get('transaction_id')
        category_name = data.get('category')
        
        if not transaction_id or not category_name:
            return jsonify({'error': 'Missing transaction_id or category'}), 400
        
        success = logic.categorize_transaction(transaction_id, category_name)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to categorize transaction'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/set_budget', methods=['POST'])
@login_required
def set_budget():
    """API endpoint to set budget for category and year"""
    if not init_logic():
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        data = request.get_json()
        category = data.get('category')
        year = data.get('year')
        amount = data.get('amount')
        
        if not category or not year or amount is None:
            return jsonify({'error': 'Missing required fields'}), 400
        
        success = logic.set_budget(category, year, float(amount))
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to set budget'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/monthly_report/<int:year>/<int:month>')
@login_required
def monthly_report(year, month):
    """API endpoint for monthly spending report"""
    if not init_logic():
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        report = logic.get_spending_report(year, month)
        return jsonify(report)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/yearly_report/<int:year>')
@login_required
def yearly_report(year):
    """API endpoint for yearly spending report"""
    if not init_logic():
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        report = logic.get_yearly_report(year)
        return jsonify(report)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    """Handle CSV file upload and import"""
    if not init_logic():
        flash('Database connection failed', 'error')
        return redirect(url_for('import_csv'))
    
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('import_csv'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('import_csv'))
    
    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Import the CSV file
            imported_count = logic.import_csv(filepath)
            
            # Clean up uploaded file
            os.remove(filepath)
            
            flash(f'Successfully imported {imported_count} transactions', 'success')
            return redirect(url_for('transactions'))
            
        except Exception as e:
            flash(f'Error importing file: {e}', 'error')
            return redirect(url_for('import_csv'))
    else:
        flash('Invalid file type. Please upload a CSV file.', 'error')
        return redirect(url_for('import_csv'))

if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)

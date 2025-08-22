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

def admin_required(f):
    """Decorator to require admin role for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') or not session.get('username'):
            return redirect(url_for('login'))
        
        # Check if user is admin
        if not init_logic():
            flash('Database connection failed', 'error')
            return redirect(url_for('index'))
        
        if not logic.db.is_admin(session.get('username')):
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
        
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
            # Get user details including role
            user_info = logic.db.get_user(username)
            
            session['logged_in'] = True
            session['username'] = username
            session['user_role'] = user_info.get('role', 'user') if user_info else 'user'
            session['is_admin'] = logic.db.is_admin(username)
            
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
        budget_data = logic.get_all_budgets()  # Fix method name
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
        report = logic.generate_yearly_report(year)
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

# Additional API endpoints needed by the frontend
@app.route('/api/categories', methods=['GET'])
@login_required
def api_categories():
    """API endpoint to get all categories"""
    if not init_logic():
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        categories = logic.get_categories()
        return jsonify(categories)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories/<category_name>', methods=['DELETE'])
@login_required
def api_delete_category(category_name):
    """API endpoint to delete a category"""
    if not init_logic():
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        # Note: This would need to be implemented in logic.py
        # For now, return not implemented
        return jsonify({'error': 'Delete category not implemented yet'}), 501
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/transactions', methods=['GET'])
@login_required
def api_transactions():
    """API endpoint to get transactions with pagination"""
    if not init_logic():
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        
        all_transactions = logic.get_transactions()
        
        # Simple pagination
        start = (page - 1) * per_page
        end = start + per_page
        transactions = all_transactions[start:end]
        
        return jsonify({
            'transactions': transactions,
            'total': len(all_transactions),
            'page': page,
            'per_page': per_page,
            'pages': (len(all_transactions) + per_page - 1) // per_page
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/uncategorized', methods=['GET'])
@login_required
def api_uncategorized():
    """API endpoint to get uncategorized transactions"""
    if not init_logic():
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        
        uncategorized = logic.get_uncategorized_transactions()
        
        # Simple pagination
        start = (page - 1) * per_page
        end = start + per_page
        transactions = uncategorized[start:end]
        
        return jsonify({
            'transactions': transactions,
            'total': len(uncategorized),
            'page': page,
            'per_page': per_page,
            'pages': (len(uncategorized) + per_page - 1) // per_page
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/budgets/<int:year>', methods=['GET'])
@login_required
def api_budgets(year):
    """API endpoint to get budgets for a specific year"""
    if not init_logic():
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        budgets = logic.get_all_budgets()  # Fix method name
        year_budgets = [b for b in budgets if b.get('year') == year]
        return jsonify(year_budgets)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/set_budget', methods=['POST'])
@login_required  
def api_set_budget():
    """API endpoint to set a single budget"""
    if not init_logic():
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        data = request.get_json()
        category = data.get('category')
        year = data.get('year')
        amount = data.get('amount')
        
        if not category or not year or amount is None:
            return jsonify({'error': 'Missing required fields: category, year, amount'}), 400
        
        success = logic.set_budget(category, int(year), float(amount))
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/budgets/<int:year>', methods=['POST'])
@login_required
def api_set_budgets(year):
    """API endpoint to set multiple budgets for a year"""
    if not init_logic():
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        data = request.get_json()
        budgets = data.get('budgets', [])
        
        success_count = 0
        for budget in budgets:
            category = budget.get('category')
            amount = budget.get('amount')
            if category and amount is not None:
                if logic.set_budget(category, year, float(amount)):
                    success_count += 1
        
        return jsonify({
            'success': True,
            'updated': success_count,
            'total': len(budgets)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reports/monthly/<int:year>/<int:month>', methods=['GET'])
@login_required
def api_monthly_report(year, month):
    """API endpoint for monthly spending report"""
    return monthly_report(year, month)

@app.route('/api/classify', methods=['POST'])
@login_required
def api_classify():
    """API endpoint to classify a single transaction"""
    if not init_logic():
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        data = request.get_json()
        transaction_id = data.get('transaction_id')
        category = data.get('category')
        
        if not transaction_id or not category:
            return jsonify({'error': 'Missing transaction_id or category'}), 400
        
        success = logic.reclassify_transaction(transaction_id, category)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/classify/batch', methods=['POST'])
@login_required
def api_classify_batch():
    """API endpoint to classify multiple transactions"""
    if not init_logic():
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        data = request.get_json()
        transactions = data.get('transactions', [])
        
        success_count = 0
        for transaction in transactions:
            transaction_id = transaction.get('transaction_id')
            category = transaction.get('category')
            if transaction_id and category:
                if logic.categorize_transaction(transaction_id, category):
                    success_count += 1
        
        return jsonify({
            'success': True,
            'classified': success_count,
            'total': len(transactions)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auto-classify', methods=['POST'])
@login_required
def api_auto_classify():
    """API endpoint for auto-classification"""
    if not init_logic():
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        # Auto-classification would need to be implemented
        # For now, return not implemented
        return jsonify({'error': 'Auto-classification not implemented yet'}), 501
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/transactions/<int:transaction_id>', methods=['DELETE'])
@login_required
def api_delete_transaction(transaction_id):
    """API endpoint to delete a single transaction"""
    if not init_logic():
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        success = logic.delete_transaction(transaction_id)
        return jsonify({'success': success, 'message': 'Transaction deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/transactions/delete/bulk', methods=['POST'])
@login_required
def api_delete_transactions_bulk():
    """API endpoint to delete multiple transactions"""
    if not init_logic():
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        data = request.get_json()
        transaction_ids = data.get('transaction_ids', [])
        
        if not transaction_ids:
            return jsonify({'error': 'No transaction IDs provided'}), 400
        
        if not isinstance(transaction_ids, list):
            return jsonify({'error': 'transaction_ids must be a list'}), 400
        
        deleted_count = logic.delete_transactions_bulk(transaction_ids)
        return jsonify({
            'success': True, 
            'deleted_count': deleted_count,
            'message': f'Successfully deleted {deleted_count} transaction(s)'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/import', methods=['POST'])
@login_required
def api_import():
    """API endpoint for CSV import"""
    # This could handle AJAX CSV imports
    # For now, redirect to the existing upload handler
    return jsonify({'error': 'Use /upload endpoint for file uploads'}), 501

@app.route('/manage_users')
@admin_required
def manage_users():
    """Admin page for managing users"""
    try:
        if not init_logic():
            flash('Database connection failed', 'error')
            return redirect(url_for('index'))
        
        users = logic.db.list_users()
        return render_template('manage_users.html', users=users)
    except Exception as e:
        flash(f'Error loading user management page: {e}', 'error')
        return redirect(url_for('index'))

@app.route('/api/users/<username>/role', methods=['POST'])
@admin_required
def update_user_role_api(username):
    """API endpoint to update user role"""
    try:
        if not init_logic():
            return jsonify({'error': 'Database connection failed'}), 500
            
        data = request.json
        new_role = data.get('role')
        
        if new_role not in ['user', 'admin']:
            return jsonify({'error': 'Invalid role. Must be user or admin'}), 400
            
        # Prevent admin from removing their own admin role
        if username == session.get('username') and new_role == 'user':
            return jsonify({'error': 'Cannot remove admin role from yourself'}), 400
            
        success = logic.db.update_user_role(username, new_role)
        if success:
            return jsonify({'message': f'User role updated to {new_role}'})
        else:
            return jsonify({'error': 'Failed to update user role'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<username>/toggle', methods=['POST'])
@admin_required
def toggle_user_status_api(username):
    """API endpoint to toggle user active status"""
    try:
        if not init_logic():
            return jsonify({'error': 'Database connection failed'}), 500
            
        # Prevent admin from deactivating themselves
        if username == session.get('username'):
            return jsonify({'error': 'Cannot deactivate your own account'}), 400
            
        success = logic.db.toggle_user_status(username)
        if success:
            return jsonify({'message': 'User status toggled successfully'})
        else:
            return jsonify({'error': 'Failed to toggle user status'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<username>', methods=['DELETE'])
@admin_required
def delete_user_api(username):
    """API endpoint to delete a user"""
    try:
        if not init_logic():
            return jsonify({'error': 'Database connection failed'}), 500
            
        # Prevent admin from deleting themselves
        if username == session.get('username'):
            return jsonify({'error': 'Cannot delete your own account'}), 400
            
        success = logic.db.delete_user(username)
        if success:
            return jsonify({'message': 'User deleted successfully'})
        else:
            return jsonify({'error': 'Failed to delete user'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)

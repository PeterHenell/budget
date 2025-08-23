"""
Web-based Budget App using Flask
Modern web UI with left-side navigation menu and user authentication
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import os
import tempfile
import json
from logic import BudgetLogic
from classifiers import AutoClassificationEngine
from background_tasks import BackgroundTaskManager, AutoClassificationTask
import pandas as pd
from werkzeug.utils import secure_filename
from datetime import datetime
from dotenv import load_dotenv
from functools import wraps
from logging_config import get_logger
from error_handling import (
    standardize_flash_message, handle_database_connection, create_error_response,
    DatabaseError, ValidationError, AuthenticationError, validate_required_fields
)
from logging_config import init_logging, get_logger
from init_database import auto_initialize_database
from init_llm import auto_initialize_llm

# Load environment variables
load_dotenv()

# Initialize logging
logger = init_logging()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-change-this-in-production')

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Store logic instance in app context for thread safety
def get_logic():
    """Get logic instance from app context (thread-safe)"""
    try:
        if not hasattr(app, 'logic_instance'):
            # Initialize connection parameters from environment
            connection_params = {
                'host': os.getenv('POSTGRES_HOST', 'postgres'),
                'port': int(os.getenv('POSTGRES_PORT', 5432)),
                'database': os.getenv('POSTGRES_DB', 'budget_db'),
                'user': os.getenv('POSTGRES_USER', 'budget_user'),
                'password': os.getenv('POSTGRES_PASSWORD', 'budget_password_2025')
            }
            
            # Auto-initialize database if needed
            logger.info("Checking if database needs initialization...")
            try:
                initialized = auto_initialize_database(connection_params)
                if initialized:
                    logger.info("Database auto-initialized successfully")
                else:
                    logger.info("Database already initialized")
            except Exception as e:
                logger.warning(f"Database auto-initialization failed: {e}")
                # Continue anyway - the BudgetLogic will handle connection issues
            
            # Auto-initialize LLM if needed
            logger.info("Checking if LLM needs initialization...")
            try:
                llm_model = auto_initialize_llm()
                if llm_model:
                    logger.info(f"LLM auto-initialized successfully with model: {llm_model}")
                    # Set environment variable for other components
                    os.environ['OLLAMA_MODEL'] = llm_model
                    os.environ['LLM_ENABLED'] = 'true'
                else:
                    logger.info("LLM not available or initialization failed")
                    os.environ['LLM_ENABLED'] = 'false'
            except Exception as e:
                logger.warning(f"LLM auto-initialization failed: {e}")
                os.environ['LLM_ENABLED'] = 'false'
            
            app.logic_instance = BudgetLogic(connection_params)
        return app.logic_instance
    except Exception as e:
        logger.error(f'Failed to initialize database connection: {e}')
        raise DatabaseError("Database connection failed", e)

def get_background_task_manager():
    """Get background task manager instance from app context (thread-safe)"""
    try:
        if not hasattr(app, 'task_manager_instance'):
            logic = get_logic()  # This ensures database is initialized
            app.task_manager_instance = BackgroundTaskManager(logic.db)
        return app.task_manager_instance
    except Exception as e:
        logger.error(f'Failed to initialize background task manager: {e}')
        raise DatabaseError("Background task manager initialization failed", e)

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
            # Check if this is an API request
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required'}), 401
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
        try:
            logic = get_logic()
        except Exception as e:
            logger.error(f'Database connection failed: {e}')
            standardize_flash_message('Database connection failed', 'error', 'error')
            return redirect(url_for('index'))
        
        if not logic.db.is_admin(session.get('username')):
            standardize_flash_message('Access denied. Admin privileges required.', 'error', 'warning')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            validate_required_fields(
                {'username': username, 'password': password}, 
                ['username', 'password']
            )
        except ValidationError as e:
            standardize_flash_message(str(e), 'error', 'warning')
            return render_template('login.html')
        
        # Get database connection 
        try:
            logic = get_logic()
        except Exception as e:
            logger.error(f'Database connection failed: {e}')
            standardize_flash_message('Database connection failed', 'error', 'error')
            return render_template('login.html')
        
        # Authenticate user
        try:
            if logic.db.authenticate_user(username, password):
                # Get user details including role
                user_info = logic.db.get_user(username)
                
                session['logged_in'] = True
                session['username'] = username
                session['user_role'] = user_info.get('role', 'user') if user_info else 'user'
                session['is_admin'] = logic.db.is_admin(username)
                
                standardize_flash_message(f'Welcome back, {username}!', 'success', 'info')
                return redirect(url_for('dashboard'))
            else:
                standardize_flash_message('Invalid username or password', 'error', 'warning')
        except Exception as e:
            logger.error(f'Authentication error: {e}')
            standardize_flash_message('Authentication failed', 'error', 'error')
        
        return render_template('login.html')
    
    return render_template('login.html')

def handle_route_errors(template_name='error.html'):
    """Decorator to handle route errors consistently"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except DatabaseError as e:
                logger.error(f'Database error in {f.__name__}: {e}')
                standardize_flash_message('Database operation failed', 'error', 'error')
                return render_template(template_name, message='Database operation failed')
            except ValidationError as e:
                logger.warning(f'Validation error in {f.__name__}: {e}')
                standardize_flash_message(str(e), 'warning', 'warning')
                return render_template(template_name, message=str(e))
            except Exception as e:
                logger.error(f'Unexpected error in {f.__name__}: {e}')
                standardize_flash_message('An unexpected error occurred', 'error', 'error')
                return render_template(template_name, message='An unexpected error occurred')
        return wrapper
    return decorator

@app.route('/logout')
def logout():
    session.clear()
    standardize_flash_message('You have been logged out successfully', 'info', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
@handle_route_errors('dashboard.html')
def index():
    """Main dashboard page"""
    logic = get_logic()  # Will raise DatabaseError if connection fails
    
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

@app.route('/transactions')
@login_required
@handle_route_errors('transactions.html')
def transactions():
    """Display all transactions"""
    logic = get_logic()  # Will raise DatabaseError if connection fails
    
    all_transactions = logic.get_transactions()
    categories = logic.get_categories()
    return render_template('transactions.html', 
                         transactions=all_transactions, 
                         categories=categories,
                         current_user=session.get('username'))

@app.route('/budgets')
@login_required
@handle_route_errors('budgets.html')
def budgets():
    """Display budget management page"""
    logic = get_logic()
    
    categories = logic.get_categories()
    budget_data = logic.get_all_budgets()  # Fix method name
    return render_template('budgets.html', 
                         categories=categories,
                         budgets=budget_data,
                         current_user=session.get('username'))

@app.route('/reports')
@login_required
@handle_route_errors('reports.html')
def reports():
    """Display reports page"""
    logic = get_logic()
    
    categories = logic.get_categories()
    return render_template('reports.html', 
                         categories=categories,
                         current_user=session.get('username'))

@app.route('/background_tasks')
@login_required
@handle_route_errors('background_tasks.html')
def background_tasks():
    """Display background tasks page"""
    return render_template('background_tasks.html',
                         current_user=session.get('username'))

@app.route('/import_csv')
@login_required
def import_csv():
    """Display CSV import page"""
    return render_template('import.html', current_user=session.get('username'))

@app.route('/uncategorized')
@login_required
@handle_route_errors('uncategorized.html')
def uncategorized():
    """Display uncategorized transactions"""
    logic = get_logic()
    
    uncategorized_transactions = logic.get_uncategorized_transactions()
    categories = logic.get_categories()
    return render_template('uncategorized.html', 
                         transactions=uncategorized_transactions,
                         categories=categories,
                         current_user=session.get('username'))

# API endpoints (all require login)
@app.route('/api/categorize_transaction', methods=['POST'])
@login_required
def categorize_transaction():
    """API endpoint to categorize a transaction"""
    try:
        logic = get_logic()
        data = request.get_json()
        
        validate_required_fields(data or {}, ['transaction_id', 'category'])
        
        transaction_id = data.get('transaction_id')
        category_name = data.get('category')
        
        success = logic.categorize_transaction(transaction_id, category_name)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to categorize transaction'}), 500
            
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except DatabaseError as e:
        return jsonify({'error': 'Database connection failed'}), 500
    except Exception as e:
        logger.error(f'Error in categorize_transaction: {e}')
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/set_budget', methods=['POST'])
@login_required
def set_budget():
    """API endpoint to set budget for category and year"""
    try:
        logic = get_logic()
        if not logic:
            return jsonify({'error': 'Database connection failed'}), 500
    
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
    try:

        logic = get_logic()

        if not logic:

            return jsonify({'error': 'Database connection failed'}), 500
        report = logic.get_spending_report(year, month)
        return jsonify(report)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/yearly_report/<int:year>')
@login_required
def yearly_report(year):
    """API endpoint for yearly spending report"""
    try:

        logic = get_logic()

        if not logic:

            return jsonify({'error': 'Database connection failed'}), 500
        report = logic.generate_yearly_report(year)
        return jsonify(report)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    """Handle CSV file upload and import"""
    try:
        logic = get_logic()
        if not logic:
            flash('Database connection failed', 'error')
            return redirect(url_for('import_csv'))
    except Exception as e:
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
    try:

        logic = get_logic()

        if not logic:

            return jsonify({'error': 'Database connection failed'}), 500
        categories = logic.get_categories()
        return jsonify(categories)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories', methods=['POST'])
@login_required
def api_create_category():
    """API endpoint to create a new category"""
    try:

        logic = get_logic()

        if not logic:

            return jsonify({'error': 'Database connection failed'}), 500
        data = request.get_json()
        name = data.get('name', '').strip()
        
        if not name:
            return jsonify({'error': 'Category name is required'}), 400
        
        logic.add_category(name)
        return jsonify({'success': True, 'message': f'Category "{name}" created successfully'})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories/<category_name>', methods=['DELETE'])
@login_required
def api_delete_category(category_name):
    """API endpoint to delete a category"""
    try:

        logic = get_logic()

        if not logic:

            return jsonify({'error': 'Database connection failed'}), 500
        logic.remove_category(category_name)
        return jsonify({'success': True, 'message': f'Category "{category_name}" deleted successfully'})
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/transactions', methods=['GET'])
@login_required
def api_transactions():
    """API endpoint to get transactions with pagination"""
    try:

        logic = get_logic()

        if not logic:

            return jsonify({'error': 'Database connection failed'}), 500
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
    try:

        logic = get_logic()

        if not logic:

            return jsonify({'error': 'Database connection failed'}), 500
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        
        uncategorized = logic.get_uncategorized_transactions()
        
        # Convert tuples to dictionaries with proper field names
        formatted_transactions = []
        for tx in uncategorized:
            tx_id, verif_num, date, description, amount, year, month = tx
            formatted_transactions.append({
                'id': tx_id,
                'verifikationsnummer': verif_num,
                'date': date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date),
                'description': description,
                'amount': float(amount),
                'year': year,
                'month': month
            })
        
        # Simple pagination on formatted data
        start = (page - 1) * per_page
        end = start + per_page
        transactions = formatted_transactions[start:end]
        
        return jsonify({
            'transactions': transactions,
            'total': len(formatted_transactions),
            'total_uncategorized': len(formatted_transactions),  # Add this for compatibility
            'page': page,
            'per_page': per_page,
            'pages': (len(formatted_transactions) + per_page - 1) // per_page
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/budgets/<int:year>', methods=['GET'])
@login_required
def api_budgets(year):
    """API endpoint to get budgets for a specific year"""
    try:

        logic = get_logic()

        if not logic:

            return jsonify({'error': 'Database connection failed'}), 500
        # Get all categories
        all_categories = logic.get_categories()
        
        # Get existing budgets for the year
        existing_budgets = logic.get_yearly_budgets(year)  # This returns {category: amount}
        
        # Create budget entries for all categories (with 0 for missing ones)
        budget_list = []
        for category in all_categories:
            budget_amount = existing_budgets.get(category, 0.0)
            budget_list.append({
                'category': category,
                'year': year,
                'yearly_budget': float(budget_amount)
            })
        
        return jsonify({'budgets': budget_list})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/set_budget', methods=['POST'])
@login_required  
def api_set_budget():
    """API endpoint to set a single budget"""
    try:

        logic = get_logic()

        if not logic:

            return jsonify({'error': 'Database connection failed'}), 500
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
def api_set_budget_for_year(year):
    """API endpoint to set a budget for a specific year"""
    try:

        logic = get_logic()

        if not logic:

            return jsonify({'error': 'Database connection failed'}), 500
        data = request.get_json()
        
        # Handle bulk budget updates
        if 'budgets' in data:
            budgets = data.get('budgets', [])
            success_count = 0
            errors = []
            
            for budget in budgets:
                category = budget.get('category')
                amount = budget.get('amount')
                
                if category and amount is not None:
                    try:
                        logic.set_budget(category, year, float(amount))
                        success_count += 1
                    except Exception as e:
                        errors.append(f'{category}: {str(e)}')
            
            return jsonify({
                'success': True,
                'saved': success_count,
                'total': len(budgets),
                'errors': errors
            })
        
        # Handle single budget update (backward compatibility)
        else:
            category = data.get('category')
            amount = data.get('amount')
            
            if not category or amount is None:
                return jsonify({'error': 'Missing required fields: category, amount'}), 400
            
            success = logic.set_budget(category, year, float(amount))
            return jsonify({'success': success, 'message': f'Budget set for {category}'})
            
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
    try:

        logic = get_logic()

        if not logic:

            return jsonify({'error': 'Database connection failed'}), 500
        data = request.get_json()
        transaction_id = data.get('transaction_id')
        category = data.get('category')
        
        if not transaction_id or not category:
            return jsonify({'error': 'Missing transaction_id or category'}), 400
        
        success = logic.reclassify_transaction(
            transaction_id, 
            category, 
            confidence=1.0, 
            classification_method='manual'
        )
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/classify/batch', methods=['POST'])
@login_required
def api_classify_batch():
    """API endpoint to classify multiple transactions"""
    try:

        logic = get_logic()

        if not logic:

            return jsonify({'error': 'Database connection failed'}), 500
        data = request.get_json()
        transactions = data.get('transactions', [])
        
        success_count = 0
        for transaction in transactions:
            transaction_id = transaction.get('transaction_id')
            category = transaction.get('category')
            if transaction_id and category:
                if logic.reclassify_transaction(
                    transaction_id, 
                    category, 
                    confidence=1.0, 
                    classification_method='manual'
                ):
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
    try:

        logic = get_logic()

        if not logic:
            return jsonify({'error': 'Database connection failed'}), 500
        data = request.get_json()
        confidence_threshold = float(data.get('confidence_threshold', 0.8))
        
        # Initialize the auto-classification engine
        engine = AutoClassificationEngine(logic)
        
        # Perform auto-classification
        classified_count, suggestions = engine.auto_classify_uncategorized(
            confidence_threshold=confidence_threshold
        )
        
        return jsonify({
            'success': True,
            'classified_count': classified_count,
            'suggestions_count': len(suggestions),
            'suggestions': suggestions[:20]  # Limit to 20 for response size
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Background Task API Routes
@app.route('/api/background-tasks', methods=['GET'])
@login_required
def api_get_background_tasks():
    """Get all background tasks for the current user"""
    try:
        task_manager = get_background_task_manager()
        
        # Get running task
        running_task = task_manager.get_running_task()
        
        # Get all tasks (without user_id filter for now)
        tasks = task_manager.get_all_tasks()
        
        return jsonify({
            'success': True,
            'running_task': running_task,
            'tasks': tasks
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/background-tasks/<int:task_id>', methods=['GET'])
@login_required
def api_get_background_task(task_id):
    """Get details of a specific background task"""
    try:
        task_manager = get_background_task_manager()
        task = task_manager.get_task_status(task_id)
        
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        return jsonify(task)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/background-tasks/auto-classify', methods=['POST'])
@login_required
def api_start_auto_classify_task():
    """Start auto-classification as a background task"""
    try:
        task_manager = get_background_task_manager()
        
        # Check if any task is already running
        if task_manager.is_task_running():
            return jsonify({
                'success': False,
                'error': 'Another background task is already running'
            }), 409
        
        logic = get_logic()
        user_id = session.get('user_id', 1)  # Default to user 1 for now
        
        # Get uncategorized count more efficiently
        total_count = logic.get_uncategorized_count()
        
        if total_count == 0:
            return jsonify({
                'success': False,
                'error': 'No uncategorized transactions to classify'
            }), 400
        
        # Create background task
        task_id = task_manager.create_task(
            task_type='auto_classify',
            task_name=f'Auto-classify {total_count} transactions',
            user_id=user_id,
            total=total_count
        )
        
        # Start the task
        auto_task = AutoClassificationTask(logic.db, logic)
        confidence_threshold = float(request.json.get('confidence_threshold', 0.7))
        
        task_manager.execute_task(task_id, auto_task.run, confidence_threshold)
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'total_transactions': total_count
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/transactions/<int:transaction_id>', methods=['DELETE'])
@login_required
def api_delete_transaction(transaction_id):
    """API endpoint to delete a single transaction"""
    try:

        logic = get_logic()

        if not logic:

            return jsonify({'error': 'Database connection failed'}), 500
        success = logic.delete_transaction(transaction_id)
        return jsonify({'success': success, 'message': 'Transaction deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/transactions/delete/bulk', methods=['POST'])
@login_required
def api_delete_transactions_bulk():
    """API endpoint to delete multiple transactions"""
    try:

        logic = get_logic()

        if not logic:

            return jsonify({'error': 'Database connection failed'}), 500
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
    try:
        logic = get_logic()
        if not logic:
            return jsonify({'error': 'Database connection failed'}), 500
    except Exception as e:
        return jsonify({'error': 'Database connection failed'}), 500
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Please upload a CSV file.'}), 400
    
    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Import the CSV file
        imported_count = logic.import_csv(filepath)
        
        # Clean up uploaded file
        os.remove(filepath)
        
        return jsonify({
            'success': True,
            'count': imported_count,
            'message': f'Successfully imported {imported_count} transactions'
        })
        
    except Exception as e:
        return jsonify({'error': f'Import failed: {str(e)}'}), 500

@app.route('/manage_users')
@admin_required
def manage_users():
    """Admin page for managing users"""
    try:
        logic = get_logic()
        if not logic:
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
        logic = get_logic()
        if not logic:
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
        logic = get_logic()
        if not logic:
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
        logic = get_logic()
        if not logic:
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

@app.route('/health')
def health_check():
    """Health check endpoint for Docker containers"""
    try:
        # Check database connectivity
        logic = get_logic()
        if logic:
            categories = logic.get_categories()
            db_status = "ok" if categories else "error"
        else:
            db_status = "no_connection"
        
        # Check LLM classifier status if available
        llm_status = "disabled"
        try:
            # Check if LLM was auto-initialized during startup
            if os.getenv('LLM_ENABLED', 'false').lower() == 'true':
                model_name = os.getenv('OLLAMA_MODEL', '')
                if model_name:
                    llm_status = f"available ({model_name})"
                else:
                    llm_status = "available"
            else:
                # Try to check with DockerLLMClassifier as fallback
                from classifiers.docker_llm_classifier import DockerLLMClassifier
                llm_classifier = DockerLLMClassifier(logic) if logic else None
                if llm_classifier and llm_classifier.available:
                    llm_status = "available"
                else:
                    llm_status = "unavailable"
        except ImportError:
            llm_status = "not_installed"
        except Exception as e:
            llm_status = f"error: {str(e)}"
        
        status = {
            'status': 'healthy' if db_status == 'ok' else 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'services': {
                'database': db_status,
                'llm_classifier': llm_status
            }
        }
        
        return jsonify(status), 200 if status['status'] == 'healthy' else 503
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 503

if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)

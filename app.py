from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import datetime, timezone, timedelta
import os
import json
import logging
import re
from logging.handlers import RotatingFileHandler
import google.generativeai as genai

# Load environment variables from .env file
from dotenv import load_dotenv

# Load .env file
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    print(f"✅ Loaded environment from: {dotenv_path}")
else:
    print(f"⚠️ .env file not found at: {dotenv_path}")

# Debug: Check if API key is loaded
api_key = os.environ.get('GEMINI_API_KEY')
if api_key:
    print(f"✅ GEMINI_API_KEY loaded successfully: {api_key[:20]}...")
else:
    print("❌ GEMINI_API_KEY not found in environment variables")

app = Flask(__name__)
# Generate a secure SECRET_KEY if not provided in environment
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or os.urandom(24).hex()
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///diary.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure logging
if not app.debug:
    if not os.path.exists('logs'):
        os.mkdir('logs')

    # Try to set up file logging, but handle permission errors gracefully
    try:
        # Test if we can actually write to the log file
        with open('logs/diary.log', 'a') as test_file:
            test_file.write('')  # Just test write access

        # If we get here, file logging should work
        # Use FileHandler instead of RotatingFileHandler to avoid rotation issues
        file_handler = logging.FileHandler('logs/diary.log')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)

        # Only log to file if setup succeeded
        file_logging_enabled = True
        app.logger.info('Diary application startup')
    except (OSError, PermissionError, IOError) as e:
        # File logging failed, use console only
        file_logging_enabled = False
        print(f"Warning: Could not set up file logging: {e}")
        print("Using console logging only for development")
        app.logger.setLevel(logging.WARNING)  # Reduce console noise
else:
    # In debug mode, use simpler logging
    file_logging_enabled = False
    app.logger.setLevel(logging.INFO)

# Console logging for development
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)
app.logger.addHandler(console_handler)

# Reduce console logging level if file logging fails
if not app.debug and not file_logging_enabled:
    console_handler.setLevel(logging.WARNING)  # Reduce noise when file logging fails

db = SQLAlchemy(app)
migrate = Migrate(app, db)
csrf = CSRFProtect(app)

# Rate limiting for security
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Initialize Gemini AI
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
gemini_model = None  # Initialize globally

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    try:
        # Try to find available models dynamically
        try:
            available_models = genai.list_models()
            working_model = None

            # Look for models that support generateContent
            for model in available_models:
                if 'generateContent' in model.supported_generation_methods:
                    try:
                        test_model = genai.GenerativeModel(model.name)
                        test_response = test_model.generate_content("Hello")
                        if test_response and test_response.text:
                            working_model = model.name
                            gemini_model = test_model
                            print(f"✅ Gemini AI initialized successfully using model: {model.name}")
                            if 'file_logging_enabled' in locals() and file_logging_enabled:
                                app.logger.info(f"Gemini AI initialized successfully using model: {model.name}")
                            break
                    except Exception:
                        continue

            if working_model:
                ai_bot_enabled = True
            else:
                # No working models found, use fallback mode
                ai_bot_enabled = True  # Enable bot with fallback responses
                gemini_model = None
                print("⚠️ No suitable Gemini models found. Using fallback mode with helpful responses.")
                if 'file_logging_enabled' in locals() and file_logging_enabled:
                    app.logger.warning("No suitable Gemini models found. Using fallback mode with helpful responses.")

        except Exception as e:
            # If list_models fails, use fallback mode
            ai_bot_enabled = True  # Enable bot with fallback responses
            gemini_model = None
            print(f"⚠️ Could not access Gemini API models: {str(e)}. Using fallback mode.")
            if 'file_logging_enabled' in locals() and file_logging_enabled:
                app.logger.warning(f"Could not access Gemini API models: {str(e)}. Using fallback mode.")

    except Exception as e:
        ai_bot_enabled = False
        if 'file_logging_enabled' in locals() and file_logging_enabled:
            app.logger.error(f"Error initializing Gemini AI: {str(e)}. AI bot features disabled.")
        else:
            print(f"❌ Error initializing Gemini AI: {str(e)}. AI bot features disabled.")
else:
    ai_bot_enabled = False
    if 'file_logging_enabled' in locals() and file_logging_enabled:
        app.logger.warning("GEMINI_API_KEY not found in environment variables. AI bot features will be disabled.")
    else:
        print("❌ GEMINI_API_KEY not found in environment variables. AI bot features disabled.")

bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ------------------ MODELS ------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime)
    current_streak = db.Column(db.Integer, default=0)
    longest_streak = db.Column(db.Integer, default=0)
    streak_start_date = db.Column(db.DateTime, nullable=True)
    last_entry_date = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    entries = db.relationship('DiaryEntry', backref='author', lazy=True, cascade='all, delete-orphan')

    def update_streak(self):
        """Update user's writing streak"""
        today = datetime.now(timezone.utc).date()

        if not self.last_entry_date:
            # First entry ever
            self.current_streak = 1
            self.longest_streak = 1
            self.streak_start_date = today
        else:
            last_entry_date = self.last_entry_date.date()

            if today == last_entry_date:
                # Same day entry, don't change streak
                pass
            elif today == last_entry_date + timedelta(days=1):
                # Consecutive day
                self.current_streak += 1
                if self.current_streak > self.longest_streak:
                    self.longest_streak = self.current_streak
                if self.current_streak == 1:
                    self.streak_start_date = today
            else:
                # Streak broken, start new one
                self.current_streak = 1
                self.streak_start_date = today

        self.last_entry_date = today
        db.session.commit()

    def get_streak_info(self):
        """Get streak information for display"""
        today = datetime.now(timezone.utc).date()

        if not self.last_entry_date:
            return {
                'current': 0,
                'longest': self.longest_streak or 0,
                'status': 'no_entries',
                'message': 'Start writing to begin your streak!'
            }

        last_entry_date = self.last_entry_date.date()

        if today == last_entry_date:
            return {
                'current': self.current_streak or 0,
                'longest': self.longest_streak or 0,
                'status': 'active_today',
                'message': f'Great! You\'ve written today. Current streak: {self.current_streak or 0} days!'
            }
        elif today == last_entry_date + timedelta(days=1):
            return {
                'current': self.current_streak or 0,
                'longest': self.longest_streak or 0,
                'status': 'can_extend',
                'message': f'Write today to extend your {self.current_streak or 0}-day streak!'
            }
        else:
            days_since = (today - last_entry_date).days
            return {
                'current': 0,
                'longest': self.longest_streak or 0,
                'status': 'broken',
                'message': f'Your streak ended {days_since} days ago. Start a new streak today!'
            }

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(7), default='#667eea')  # Hex color
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
class EntryTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    mood = db.Column(db.String(20), nullable=True)
    weather = db.Column(db.String(50), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    tags = db.Column(db.Text, nullable=True)  # JSON string of tags
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user = db.relationship('User', backref='templates')
    category = db.relationship('Category', backref='templates')

    def get_tags_list(self):
        """Convert tags JSON string to list"""
        if self.tags:
            try:
                return json.loads(self.tags)
            except:
                return []
        return []
    
    def set_tags_list(self, tags_list):
        """Convert tags list to JSON string"""
        self.tags = json.dumps(tags_list) if tags_list else None

class DiaryEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    title = db.Column(db.String(200), nullable=True)  # Optional title
    content = db.Column(db.Text, nullable=False)
    mood = db.Column(db.String(20), nullable=True)  # happy, sad, excited, etc.
    weather = db.Column(db.String(50), nullable=True)  # sunny, rainy, etc.
    location = db.Column(db.String(100), nullable=True)
    tags = db.Column(db.Text, nullable=True)  # JSON string of tags
    is_private = db.Column(db.Boolean, default=True)
    is_favorite = db.Column(db.Boolean, default=False)  # Pin/favorite entries
    word_count = db.Column(db.Integer, default=0)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Indexes for better query performance
    __table_args__ = (
        db.Index('idx_user_timestamp', 'user_id', 'timestamp'),
        db.Index('idx_user_category', 'user_id', 'category_id'),
    )
    
    def get_tags_list(self):
        """Convert tags JSON string to list"""
        if self.tags:
            try:
                return json.loads(self.tags)
            except:
                return []
        return []
    
    def set_tags_list(self, tags_list):
        """Convert tags list to JSON string"""
        self.tags = json.dumps(tags_list) if tags_list else None

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ------------------ UTILITY FUNCTIONS ------------------
def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number"
    return True, "Password is valid"

def validate_username(username):
    """Validate username"""
    if len(username) < 3:
        return False, "Username must be at least 3 characters long"
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        return False, "Username can only contain letters, numbers, and underscores"
    return True, "Username is valid"

# ------------------ ROUTES ------------------
@app.route('/')
def home():
    return render_template('index.html')

# Register
@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("10 per hour")
def register():
    app.logger.info(f'Register page accessed - Method: {request.method}')
    
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        
        app.logger.info(f'Registration attempt for username: {username}')
        
        # Validate username
        is_valid_username, username_msg = validate_username(username)
        if not is_valid_username:
            app.logger.warning(f'Invalid username: {username} - {username_msg}')
            flash(username_msg, 'danger')
            return render_template('register.html')
        
        # Validate password
        is_valid_password, password_msg = validate_password(password)
        if not is_valid_password:
            app.logger.warning(f'Invalid password for user: {username}')
            flash(password_msg, 'danger')
            return render_template('register.html')
        
        # Check if username already exists
        if User.query.filter_by(username=username).first():
            app.logger.warning(f'Username already exists: {username}')
            flash('Username already exists!', 'danger')
            return render_template('register.html')
        
        # Create user
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, password=hashed_password)
        try:
            db.session.add(user)
            db.session.commit()
            
            # Create default categories for new user
            default_categories = [
                {'name': 'General', 'color': '#667eea'},
                {'name': 'Work', 'color': '#f39c12'},
                {'name': 'Personal', 'color': '#e74c3c'},
                {'name': 'Travel', 'color': '#2ecc71'},
                {'name': 'Health', 'color': '#9b59b6'}
            ]
            
            for cat_data in default_categories:
                category = Category(name=cat_data['name'], color=cat_data['color'], user_id=user.id)
                db.session.add(category)
            
            db.session.commit()
            
            app.logger.info(f'User registered successfully: {username} (ID: {user.id})')
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Error creating user {username}: {str(e)}')
            flash('An error occurred while creating your account. Please try again.', 'danger')
    
    return render_template('register.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("20 per minute")
def login():
    app.logger.info(f'Login page accessed - Method: {request.method}')
    
    if request.method == 'POST':
        username = request.form['username']
        app.logger.info(f'Login attempt for username: {username}')
        
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, request.form['password']):
            login_user(user)
            user.last_login = datetime.now(timezone.utc)
            db.session.commit()
            
            app.logger.info(f'User logged in successfully: {username} (ID: {user.id})')
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('dashboard'))
        
        app.logger.warning(f'Failed login attempt for username: {username}')
        flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Show 10 entries per page
    
    # Get entries with pagination, ordered by favorites first, then most recent
    entries_pagination = DiaryEntry.query.filter_by(user_id=current_user.id)\
        .order_by(DiaryEntry.is_favorite.desc(), DiaryEntry.timestamp.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    entries = entries_pagination.items

    # Ensure all entries have a valid timestamp (if any entry has None)
    for entry in entries:
        if entry.timestamp is None:
            entry.timestamp = datetime.now()
            db.session.commit()

    return render_template('dashboard.html', 
                         entries=entries, 
                         pagination=entries_pagination)

# Write Entry
@app.route('/write', methods=['GET', 'POST'])
@login_required
@limiter.limit("20 per hour")
def write():
    app.logger.info(f'Write page accessed by user: {current_user.username}')
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form['content'].strip()
        category_id = request.form.get('category_id')
        mood = request.form.get('mood')
        weather = request.form.get('weather')
        location = request.form.get('location', '').strip()
        tags_input = request.form.get('tags', '').strip()
        is_private = request.form.get('is_private') == 'on'
        
        app.logger.info(f'New entry submission by {current_user.username} - Title: {title}, Length: {len(content)}')
        
        if content:
            # Basic content validation
            if len(content) < 10:
                app.logger.warning(f'Entry too short by {current_user.username}')
                flash('Entry must be at least 10 characters long', 'warning')
                return render_template('write.html')
            
            if len(content) > 10000:
                app.logger.warning(f'Entry too long by {current_user.username}')
                flash('Entry is too long (maximum 10,000 characters)', 'warning')
                return render_template('write.html')
            
            # Process tags
            tags_list = []
            if tags_input:
                tags_list = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
            
            # Calculate word count
            word_count = len(content.split())
            
            entry = DiaryEntry(
                user_id=current_user.id,
                title=title if title else None,
                content=content,
                category_id=int(category_id) if category_id else None,
                mood=mood if mood else None,
                weather=weather if weather else None,
                location=location if location else None,
                is_private=is_private,
                word_count=word_count
            )
            entry.set_tags_list(tags_list)
            
            try:
                db.session.add(entry)
                db.session.commit()
                
                # Update user's writing streak
                current_user.update_streak()
                
                app.logger.info(f'Entry created successfully by {current_user.username} (ID: {entry.id}, Words: {word_count})')
                flash('Entry saved successfully!', 'success')
                return redirect(url_for('dashboard'))
            except Exception as e:
                db.session.rollback()
                app.logger.error(f'Error saving entry by {current_user.username}: {str(e)}')
                flash('An error occurred while saving your entry. Please try again.', 'danger')
        else:
            app.logger.warning(f'Empty entry submission by {current_user.username}')
            flash('Entry content cannot be empty!', 'danger')
    
    # Get user's categories for the form
    categories = Category.query.filter_by(user_id=current_user.id).all()
    
    # Check if using a template
    template_content = request.args.get('template_content', '')
    template_title = request.args.get('template_title', '')
    
    return render_template('write.html', 
                         categories=categories,
                         template_content=template_content,
                         template_title=template_title)

# Search Entries
@app.route('/search', methods=['GET'])
@login_required
def search():
    query = request.args.get('query', '').strip()
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    # Start with base query for current user
    base_query = DiaryEntry.query.filter_by(user_id=current_user.id)
    
    # Add text search if query provided
    if query:
        base_query = base_query.filter(DiaryEntry.content.contains(query))
    
    # Add date filtering if dates provided
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            base_query = base_query.filter(DiaryEntry.timestamp >= from_date)
        except ValueError:
            flash('Invalid date format for "from" date', 'warning')
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d')
            # Add one day to include the entire "to" date
            to_date = to_date.replace(hour=23, minute=59, second=59)
            base_query = base_query.filter(DiaryEntry.timestamp <= to_date)
        except ValueError:
            flash('Invalid date format for "to" date', 'warning')
    
    # Order by most recent first
    results = base_query.order_by(DiaryEntry.timestamp.desc()).all()
    
    return render_template('search_results.html', 
                         results=results, 
                         query=query,
                         date_from=date_from,
                         date_to=date_to)

# Edit Entry
@app.route('/edit/<int:entry_id>', methods=['GET', 'POST'])
@login_required
def edit_entry(entry_id):
    entry = DiaryEntry.query.filter_by(id=entry_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        content = request.form['content'].strip()
        if content:
            # Basic content validation
            if len(content) < 10:
                flash('Entry must be at least 10 characters long', 'warning')
                return render_template('edit_entry.html', entry=entry)
            
            if len(content) > 10000:
                flash('Entry is too long (maximum 10,000 characters)', 'warning')
                return render_template('edit_entry.html', entry=entry)
            
            try:
                entry.content = content
                db.session.commit()
                flash('Entry updated successfully!', 'success')
                return redirect(url_for('dashboard'))
            except Exception as e:
                db.session.rollback()
                flash('An error occurred while updating your entry. Please try again.', 'danger')
    else:
            flash('Entry content cannot be empty!', 'danger')
    
    return render_template('edit_entry.html', entry=entry)

# Delete Entry
@app.route('/delete/<int:entry_id>', methods=['POST'])
@login_required
def delete_entry(entry_id):
    entry = DiaryEntry.query.filter_by(id=entry_id, user_id=current_user.id).first_or_404()
    
    try:
        db.session.delete(entry)
        db.session.commit()
        app.logger.info(f'Entry deleted by {current_user.username} - Entry ID: {entry_id}')
        flash('Entry deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error deleting entry {entry_id} by {current_user.username}: {str(e)}')
        flash('An error occurred while deleting the entry. Please try again.', 'danger')
    
    return redirect(url_for('dashboard'))

# View Single Entry
@app.route('/entry/<int:entry_id>')
@login_required
def view_entry(entry_id):
    app.logger.info(f'Entry view requested by {current_user.username} - Entry ID: {entry_id}')
    entry = DiaryEntry.query.filter_by(id=entry_id, user_id=current_user.id).first_or_404()
    return render_template('view_entry.html', entry=entry)

# Categories Management
@app.route('/categories')
@login_required
def categories():
    app.logger.info(f'Categories page accessed by {current_user.username}')
    user_categories = Category.query.filter_by(user_id=current_user.id).all()
    return render_template('categories.html', categories=user_categories)

@app.route('/categories/create', methods=['POST'])
@login_required
@limiter.limit("10 per hour")
def create_category():
    name = request.form['name'].strip()
    color = request.form.get('color', '#667eea')
    
    app.logger.info(f'Category creation attempt by {current_user.username} - Name: {name}')
    
    if not name:
        flash('Category name is required', 'danger')
        return redirect(url_for('categories'))
    
    # Check if category already exists for this user
    existing = Category.query.filter_by(user_id=current_user.id, name=name).first()
    if existing:
        flash('Category already exists', 'warning')
        return redirect(url_for('categories'))
    
    try:
        category = Category(name=name, color=color, user_id=current_user.id)
        db.session.add(category)
        db.session.commit()
        
        app.logger.info(f'Category created successfully by {current_user.username} - ID: {category.id}')
        flash('Category created successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error creating category by {current_user.username}: {str(e)}')
        flash('Error creating category', 'danger')
    
    return redirect(url_for('categories'))

# Entry Templates Management
@app.route('/templates')
@login_required
def templates():
    app.logger.info(f'Templates page accessed by {current_user.username}')
    user_templates = EntryTemplate.query.filter_by(user_id=current_user.id).all()
    return render_template('templates.html', templates=user_templates)

@app.route('/templates/create', methods=['POST'])
@login_required
def create_template():
    name = request.form['name'].strip()
    content = request.form['content'].strip()
    category_id = request.form.get('category_id')
    mood = request.form.get('mood')
    weather = request.form.get('weather')
    location = request.form.get('location', '').strip()
    tags_input = request.form.get('tags', '').strip()
    is_default = request.form.get('is_default') == 'on'
    
    app.logger.info(f'Template creation attempt by {current_user.username} - Name: {name}')
    
    if not name or not content:
        flash('Template name and content are required', 'danger')
        return redirect(url_for('templates'))
    
    # Process tags
    tags_list = []
    if tags_input:
        tags_list = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
    
    try:
        template = EntryTemplate(
            user_id=current_user.id,
            name=name,
            content=content,
            category_id=int(category_id) if category_id else None,
            mood=mood if mood else None,
            weather=weather if weather else None,
            location=location if location else None,
            is_default=is_default
        )
        template.set_tags_list(tags_list)
        
        db.session.add(template)
        db.session.commit()
        
        app.logger.info(f'Template created successfully by {current_user.username} - ID: {template.id}')
        flash('Template created successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error creating template by {current_user.username}: {str(e)}')
        flash('Error creating template', 'danger')
    
    return redirect(url_for('templates'))

@app.route('/templates/use/<int:template_id>')
@login_required
def use_template(template_id):
    template = EntryTemplate.query.filter_by(id=template_id, user_id=current_user.id).first_or_404()
    
    # Get user's categories for the form
    categories = Category.query.filter_by(user_id=current_user.id).all()
    
    return render_template('write.html', 
                         categories=categories,
                         template=template,
                         template_content=template.content,
                         template_title=template.name)

@app.route('/templates/delete/<int:template_id>', methods=['POST'])
@login_required
def delete_template(template_id):
    template = EntryTemplate.query.filter_by(id=template_id, user_id=current_user.id).first_or_404()
    
    try:
        db.session.delete(template)
        db.session.commit()
        app.logger.info(f'Template deleted by {current_user.username} - ID: {template_id}')
        flash('Template deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error deleting template {template_id}: {str(e)}')
        flash('An error occurred while deleting the template. Please try again.', 'danger')
    
    return redirect(url_for('templates'))

# Statistics Dashboard
@app.route('/stats')
@login_required
def stats():
    app.logger.info(f'Statistics page accessed by {current_user.username}')
    
    # Get user's entries
    entries = DiaryEntry.query.filter_by(user_id=current_user.id).all()
    
    # Calculate statistics
    total_entries = len(entries)
    total_words = sum(entry.word_count for entry in entries)
    avg_words = total_words / total_entries if total_entries > 0 else 0
    
    # Entries by month (last 12 months)
    from collections import defaultdict
    monthly_stats = defaultdict(int)
    for entry in entries:
        month_key = entry.timestamp.strftime('%Y-%m')
        monthly_stats[month_key] += 1
    
    # Mood statistics
    mood_stats = defaultdict(int)
    for entry in entries:
        if entry.mood:
            mood_stats[entry.mood] += 1
    
    # Mood trends over time (last 30 days)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    recent_entries = []

    for entry in entries:
        if entry.timestamp:
            # Handle timezone-aware vs naive datetime comparison
            try:
                if entry.timestamp.tzinfo is None:
                    # Entry timestamp is naive, compare with naive version of thirty_days_ago
                    thirty_days_ago_naive = thirty_days_ago.replace(tzinfo=None)
                    if entry.timestamp >= thirty_days_ago_naive:
                        recent_entries.append(entry)
                else:
                    # Entry timestamp is aware, compare directly
                    if entry.timestamp >= thirty_days_ago:
                        recent_entries.append(entry)
            except (TypeError, AttributeError):
                # Fallback: try naive comparison
                try:
                    thirty_days_ago_naive = thirty_days_ago.replace(tzinfo=None)
                    if entry.timestamp.replace(tzinfo=timezone.utc) >= thirty_days_ago_naive:
                        recent_entries.append(entry)
                except:
                    # If all else fails, include the entry
                    recent_entries.append(entry)
    
    mood_trends = defaultdict(list)
    for entry in recent_entries:
        if entry.mood and entry.timestamp:
            day_key = entry.timestamp.strftime('%Y-%m-%d')
            mood_trends[day_key].append(entry.mood)
    
    # Most common mood
    most_common_mood = max(mood_stats.items(), key=lambda x: x[1])[0] if mood_stats else None
    
    # Mood improvement tracking (comparing first half vs second half of entries)
    if len(entries) >= 10:
        midpoint = len(entries) // 2
        first_half = entries[midpoint:]
        second_half = entries[:midpoint]
        
        first_half_moods = [entry.mood for entry in first_half if entry.mood]
        second_half_moods = [entry.mood for entry in second_half if entry.mood]
        
        first_half_positive = len([m for m in first_half_moods if m in ['😊 Happy', '🎉 Excited', '😌 Peaceful']])
        second_half_positive = len([m for m in second_half_moods if m in ['😊 Happy', '🎉 Excited', '😌 Peaceful']])
        
        mood_improvement = second_half_positive - first_half_positive
    else:
        mood_improvement = None
    
    # Category statistics
    category_stats = defaultdict(int)
    for entry in entries:
        if entry.category_id:
            category = Category.query.get(entry.category_id)
            if category:
                category_stats[category.name] += 1
    
    # Most used tags
    tag_stats = defaultdict(int)
    for entry in entries:
        for tag in entry.get_tags_list():
            tag_stats[tag] += 1
    
    stats_data = {
        'total_entries': total_entries,
        'total_words': total_words,
        'avg_words': round(avg_words, 1),
        'monthly_stats': dict(monthly_stats),
        'mood_stats': dict(mood_stats),
        'mood_trends': dict(mood_trends),
        'most_common_mood': most_common_mood,
        'mood_improvement': mood_improvement,
        'category_stats': dict(category_stats),
        'tag_stats': dict(sorted(tag_stats.items(), key=lambda x: x[1], reverse=True)[:10])
    }
    
    return render_template('stats.html', stats=stats_data)

# Backup/Restore Routes
@app.route('/backup', methods=['GET', 'POST'])
@login_required
@limiter.limit("10 per hour")
def backup_restore():
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'create_backup':
            return create_backup()
        elif action == 'restore_backup':
            if 'backup_file' not in request.files:
                flash('No backup file provided', 'danger')
                return redirect(url_for('backup_restore'))
            
            file = request.files['backup_file']
            if file.filename == '':
                flash('No backup file selected', 'danger')
                return redirect(url_for('backup_restore'))
            
            if file and file.filename.endswith('.json'):
                return restore_backup(file)
            else:
                flash('Please upload a valid JSON backup file', 'danger')
                return redirect(url_for('backup_restore'))
    
    return render_template('backup_restore.html')

def create_backup():
    """Create a complete backup of user's data"""
    try:
        # Get all user data
        user_data = {
            'user': {
                'username': current_user.username,
                'created_at': current_user.created_at.isoformat() if current_user.created_at else None
            },
            'categories': [],
            'entries': [],
            'templates': [],
            'backup_date': datetime.now(timezone.utc).isoformat()
        }
        
        # Get categories
        categories = Category.query.filter_by(user_id=current_user.id).all()
        for category in categories:
            user_data['categories'].append({
                'id': category.id,
                'name': category.name,
                'color': category.color,
                'created_at': category.created_at.isoformat() if category.created_at else None
            })
        
        # Get entries
        entries = DiaryEntry.query.filter_by(user_id=current_user.id).all()
        for entry in entries:
            entry_data = {
                'id': entry.id,
                'title': entry.title,
                'content': entry.content,
                'mood': entry.mood,
                'weather': entry.weather,
                'location': entry.location,
                'tags': entry.get_tags_list(),
                'is_private': entry.is_private,
                'is_favorite': entry.is_favorite,
                'word_count': entry.word_count,
                'timestamp': entry.timestamp.isoformat() if entry.timestamp else None,
                'updated_at': entry.updated_at.isoformat() if entry.updated_at else None
            }
            
            # Add category info if exists
            if entry.category_id:
                category = Category.query.get(entry.category_id)
                entry_data['category'] = category.name if category else None
            
            user_data['entries'].append(entry_data)
        
        # Get templates
        templates = EntryTemplate.query.filter_by(user_id=current_user.id).all()
        for template in templates:
            template_data = {
                'id': template.id,
                'name': template.name,
                'content': template.content,
                'mood': template.mood,
                'weather': template.weather,
                'location': template.location,
                'tags': template.get_tags_list(),
                'is_default': template.is_default,
                'created_at': template.created_at.isoformat() if template.created_at else None
            }
            
            if template.category_id:
                category = Category.query.get(template.category_id)
                template_data['category'] = category.name if category else None
            
            user_data['templates'].append(template_data)
        
        # Create response
        response = jsonify(user_data)
        filename = f"diary_backup_{current_user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        
        app.logger.info(f'Backup created by {current_user.username}')
        flash('Backup created successfully!', 'success')
        return response
        
    except Exception as e:
        app.logger.error(f'Error creating backup for {current_user.username}: {str(e)}')
        flash('An error occurred while creating the backup. Please try again.', 'danger')
        return redirect(url_for('backup_restore'))

def restore_backup(file):
    """Restore data from backup file"""
    try:
        backup_data = json.load(file)
        
        # Validate backup structure
        if not all(key in backup_data for key in ['user', 'categories', 'entries', 'templates']):
            flash('Invalid backup file format', 'danger')
            return redirect(url_for('backup_restore'))
        
        # Clear existing data (optional - ask user?)
        # For now, we'll append to existing data
        
        # Restore categories
        for cat_data in backup_data['categories']:
            # Check if category already exists
            existing = Category.query.filter_by(user_id=current_user.id, name=cat_data['name']).first()
            if not existing:
                category = Category(
                    name=cat_data['name'],
                    color=cat_data['color'],
                    user_id=current_user.id
                )
                db.session.add(category)
        
        # Restore entries
        for entry_data in backup_data['entries']:
            # Check if entry already exists (by ID)
            existing = DiaryEntry.query.filter_by(id=entry_data['id'], user_id=current_user.id).first()
            if not existing:
                entry = DiaryEntry(
                    user_id=current_user.id,
                    title=entry_data.get('title'),
                    content=entry_data['content'],
                    mood=entry_data.get('mood'),
                    weather=entry_data.get('weather'),
                    location=entry_data.get('location'),
                    is_private=entry_data.get('is_private', True),
                    is_favorite=entry_data.get('is_favorite', False),
                    word_count=entry_data.get('word_count', 0)
                )
                entry.set_tags_list(entry_data.get('tags', []))
                
                # Set timestamp if provided
                if entry_data.get('timestamp'):
                    entry.timestamp = datetime.fromisoformat(entry_data['timestamp'])
                
                db.session.add(entry)
        
        # Restore templates
        for template_data in backup_data['templates']:
            existing = EntryTemplate.query.filter_by(id=template_data['id'], user_id=current_user.id).first()
            if not existing:
                template = EntryTemplate(
                    user_id=current_user.id,
                    name=template_data['name'],
                    content=template_data['content'],
                    mood=template_data.get('mood'),
                    weather=template_data.get('weather'),
                    location=template_data.get('location'),
                    is_default=template_data.get('is_default', False)
                )
                template.set_tags_list(template_data.get('tags', []))
                
                if template_data.get('created_at'):
                    template.created_at = datetime.fromisoformat(template_data['created_at'])
                
                db.session.add(template)
        
        db.session.commit()
        
        app.logger.info(f'Backup restored by {current_user.username}')
        flash('Backup restored successfully!', 'success')
        
    except json.JSONDecodeError:
        flash('Invalid JSON backup file', 'danger')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error restoring backup for {current_user.username}: {str(e)}')
        flash('An error occurred while restoring the backup. Please try again.', 'danger')
    
    return redirect(url_for('backup_restore'))

# AI Bot Routes
@app.route('/bot')
@login_required
def ai_bot():
    """AI Bot chat interface"""
    if not ai_bot_enabled:
        flash('AI Bot is not available. Please check API configuration.', 'warning')
        return redirect(url_for('dashboard'))

    return render_template('bot.html')

@app.route('/bot/chat', methods=['POST'])
@login_required
@limiter.limit("30 per hour")
@csrf.exempt  # Exempt CSRF for AJAX requests from authenticated users
def bot_chat():
    """Handle AI bot chat requests"""
    if not ai_bot_enabled:
        return jsonify({'error': 'AI Bot is currently unavailable. Please try again later.'}), 503

    # Skip CSRF validation for AJAX requests from authenticated users
    # The user is already authenticated via @login_required

    try:
        user_message = request.json.get('message', '').strip()
        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400

        # Check if we have a working Gemini model
        if gemini_model:
            # Use real AI
            context_prompt = f"""
            You are an AI writing assistant for a personal diary application. The user is {current_user.username}.
            Help them with writing prompts, suggestions, or creative inspiration for their diary entries.

            Common requests include:
            - Writing prompts for different moods or situations
            - Creative writing suggestions
            - Reflection questions
            - Journaling techniques
            - Overcoming writer's block
            - Daily gratitude prompts

            Keep responses helpful, encouraging, and focused on personal growth and self-reflection.
            Responses should be conversational and supportive.

            User message: {user_message}
            """

            response = gemini_model.generate_content(context_prompt)

            if response and response.text:
                return jsonify({
                    'success': True,
                    'response': response.text.strip(),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            else:
                return jsonify({'error': 'No response generated from AI model'}), 500
        else:
            # Use fallback responses
            fallback_responses = [
                "That's a great question! While I'm getting set up, here are some writing prompts to inspire you: What made you smile today? What challenged you? What are you grateful for?",
                "I love helping with journaling! Try this approach: Start by describing your day, then reflect on one positive moment and one thing you learned.",
                "Journaling is such a powerful tool for self-reflection! Consider writing about: What emotions are you feeling right now? What would you tell your future self?",
                "I'm here to help with your writing journey! A good prompt to try: 'If I could go back and give advice to my younger self, what would I say?'",
                "Writing can be therapeutic! Try reflecting on: What surprised you today? What are you looking forward to? What challenged your perspective?",
                "Here's a helpful journaling technique: Write about three things you're grateful for, then explore why each one matters to you.",
                "Try this reflective prompt: What did you learn today that you didn't expect to learn?",
                "A creative writing idea: Imagine your perfect day and describe it in detail, then think about one small step to make it real."
            ]

            import random
            response_text = random.choice(fallback_responses)

            return jsonify({
                'success': True,
                'response': response_text,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })

    except Exception as e:
        app.logger.error(f'Bot chat error for {current_user.username}: {str(e)}')
        return jsonify({'error': 'An error occurred while processing your request. Please try again later.'}), 500

@app.route('/bot/suggest_prompts', methods=['GET'])
@login_required
@limiter.limit("20 per hour")
@csrf.exempt  # Exempt CSRF for AJAX requests from authenticated users
def suggest_prompts():
    """Get AI-generated writing prompts"""
    if not ai_bot_enabled:
        return jsonify({'error': 'AI Bot is currently unavailable. Please try again later.'}), 503

    try:
        mood = request.args.get('mood', 'neutral')
        category = request.args.get('category', 'general')

        # Check if we have a working Gemini model
        if gemini_model:
            # Use real AI for prompts
            prompt_request = f"""
            Generate 3 creative and thoughtful writing prompts for a diary entry.
            Mood: {mood}
            Category: {category}

            Make them personal, reflective, and encouraging for self-discovery.
            Each prompt should be 1-2 sentences long and inspiring.
            """

            response = gemini_model.generate_content(prompt_request)

            if response and response.text:
                # Parse the response into individual prompts
                prompts = [p.strip() for p in response.text.split('\n') if p.strip() and not p.strip().isdigit()]
                if len(prompts) < 3:
                    # Fallback prompts if parsing fails
                    prompts = [
                        "What made you smile today, and why?",
                        "Reflect on a challenge you faced and what you learned from it.",
                        "What are you grateful for in this moment?"
                    ]

                return jsonify({
                    'success': True,
                    'prompts': prompts[:3]
                })
            else:
                return jsonify({'error': 'No prompts generated from AI model'}), 500
        else:
            # Use fallback prompts
            fallback_prompts = {
                'gratitude': [
                    "What three things are you most grateful for today?",
                    "Who made a positive impact on your life recently?",
                    "What simple pleasures brought you joy this week?"
                ],
                'reflection': [
                    "What did you learn about yourself today?",
                    "How have you grown in the past month?",
                    "What would you do differently if you could relive today?"
                ],
                'creativity': [
                    "If you could create anything right now, what would it be?",
                    "What inspires your creativity the most?",
                    "Describe your perfect creative day."
                ],
                'mindfulness': [
                    "What are you feeling in this exact moment?",
                    "How can you be more present today?",
                    "What thoughts are occupying your mind?"
                ],
                'motivation': [
                    "What motivates you to keep going?",
                    "What small step can you take toward your goals today?",
                    "Who inspires you and why?"
                ]
            }

            # Get prompts for the requested mood, or use general ones
            prompts = fallback_prompts.get(mood.lower(), [
                "What made you smile today?",
                "What challenged you and what did you learn?",
                "What are you grateful for right now?"
            ])

            return jsonify({
                'success': True,
                'prompts': prompts
            })

    except Exception as e:
        app.logger.error(f'Prompt generation error for {current_user.username}: {str(e)}')
        return jsonify({'error': 'An error occurred while generating prompts. Please try again later.'}), 500

# Export Entries
@app.route('/export')
@login_required
def export_entries():
    app.logger.info(f'Export requested by {current_user.username}')
    
    format_type = request.args.get('format', 'txt')
    entries = DiaryEntry.query.filter_by(user_id=current_user.id).order_by(DiaryEntry.timestamp.desc()).all()
    
    if format_type == 'json':
        export_data = []
        for entry in entries:
            # Get category name if exists
            category_name = None
            if entry.category_id:
                category = db.session.get(Category, entry.category_id)
                category_name = category.name if category else None
            
            export_data.append({
                'id': entry.id,
                'title': entry.title,
                'content': entry.content,
                'mood': entry.mood,
                'weather': entry.weather,
                'location': entry.location,
                'tags': entry.get_tags_list(),
                'category': category_name,
                'timestamp': entry.timestamp.isoformat(),
                'word_count': entry.word_count
            })
        
        response = jsonify(export_data)
        response.headers['Content-Disposition'] = f'attachment; filename=diary_export_{datetime.now().strftime("%Y%m%d")}.json'
        return response
    
    else:  # txt format
        export_text = f"My Diary Export - {datetime.now().strftime('%Y-%m-%d')}\n"
        export_text += "=" * 50 + "\n\n"
        
        for entry in entries:
            # Get category name if exists
            category_name = None
            if entry.category_id:
                category = db.session.get(Category, entry.category_id)
                category_name = category.name if category else None
            
            export_text += f"Entry #{entry.id}\n"
            export_text += f"Date: {entry.timestamp.strftime('%Y-%m-%d %H:%M')}\n"
            if entry.title:
                export_text += f"Title: {entry.title}\n"
            if entry.mood:
                export_text += f"Mood: {entry.mood}\n"
            if entry.weather:
                export_text += f"Weather: {entry.weather}\n"
            if entry.location:
                export_text += f"Location: {entry.location}\n"
            if category_name:
                export_text += f"Category: {category_name}\n"
            if entry.get_tags_list():
                export_text += f"Tags: {', '.join(entry.get_tags_list())}\n"
            export_text += f"Words: {entry.word_count}\n"
            export_text += "-" * 30 + "\n"
            export_text += entry.content + "\n\n"
        
        response = app.response_class(
            response=export_text,
            status=200,
            mimetype='text/plain'
        )
        response.headers['Content-Disposition'] = f'attachment; filename=diary_export_{datetime.now().strftime("%Y%m%d")}.txt'
        return response

# Toggle Favorite/Pin Entry
@app.route('/toggle_favorite/<int:entry_id>', methods=['POST'])
@login_required
@limiter.limit("50 per hour")
def toggle_favorite(entry_id):
    entry = DiaryEntry.query.filter_by(id=entry_id, user_id=current_user.id).first_or_404()
    
    try:
        entry.is_favorite = not entry.is_favorite
        db.session.commit()
        
        status = 'pinned' if entry.is_favorite else 'unpinned'
        app.logger.info(f'Entry {entry_id} {status} by {current_user.username}')
        
        return jsonify({
            'success': True,
            'is_favorite': entry.is_favorite,
            'message': f'Entry {status} successfully!'
        })
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error toggling favorite for entry {entry_id}: {str(e)}')
        return jsonify({
            'success': False,
            'message': 'An error occurred. Please try again.'
        }), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Ensure database tables are created before starting the app
# Initialize database tables for production deployment
with app.app_context():
    try:
        db.create_all()
        print('Database tables created successfully for production')
    except Exception as e:
        print(f'Database initialization warning: {e}')

    # Production deployment configuration\n    port = int(os.environ.get("PORT", 5000))\n    app.run(host="0.0.0.0", port=port, debug=False)


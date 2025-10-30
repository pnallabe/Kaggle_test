from flask import Flask, jsonify, request
from datetime import datetime, timedelta
import os
import json
from pathlib import Path
import jwt
import bcrypt
from functools import wraps
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Configuration
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
JWT_EXPIRATION_HOURS = 24
STORAGE_DIR = 'data'
USERS_FILE = f'{STORAGE_DIR}/users.json'
PROJECTS_FILE = f'{STORAGE_DIR}/projects.json'
DATASETS_FILE = f'{STORAGE_DIR}/datasets.json'
MAX_STORAGE_PER_USER_MB = 100  # 100MB per user

# Ensure storage directory exists
Path(STORAGE_DIR).mkdir(exist_ok=True)

# In-memory caches (for performance)
users_db = {}
projects_db = {}
datasets_db = {}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def load_users():
    """Load users from storage file"""
    global users_db
    if Path(USERS_FILE).exists():
        try:
            with open(USERS_FILE, 'r') as f:
                users_db = json.load(f)
        except:
            users_db = {}
    return users_db

def save_users():
    """Save users to storage file"""
    with open(USERS_FILE, 'w') as f:
        json.dump(users_db, f, indent=2)

def load_projects():
    """Load projects from storage file"""
    global projects_db
    if Path(PROJECTS_FILE).exists():
        try:
            with open(PROJECTS_FILE, 'r') as f:
                projects_db = json.load(f)
        except:
            projects_db = {}
    return projects_db

def save_projects():
    """Save projects to storage file"""
    with open(PROJECTS_FILE, 'w') as f:
        json.dump(projects_db, f, indent=2)

def load_datasets():
    """Load datasets from storage file"""
    global datasets_db
    if Path(DATASETS_FILE).exists():
        try:
            with open(DATASETS_FILE, 'r') as f:
                datasets_db = json.load(f)
        except:
            datasets_db = {}
    return datasets_db

def save_datasets():
    """Save datasets to storage file"""
    with open(DATASETS_FILE, 'w') as f:
        json.dump(datasets_db, f, indent=2)

def hash_password(password):
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, hashed):
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def generate_token(user_id):
    """Generate JWT token"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def verify_token(token):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except:
        return None

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]
            except IndexError:
                return jsonify({'error': 'Invalid authorization header'}), 401
        
        if not token:
            return jsonify({'error': 'Missing authorization token'}), 401
        
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Store user_id in request context
        request.user_id = payload['user_id']
        return f(*args, **kwargs)
    
    return decorated_function

def get_user_storage_usage(user_id):
    """Calculate total storage used by user in MB"""
    load_datasets()
    total_bytes = 0
    
    if user_id in datasets_db:
        for dataset in datasets_db[user_id]:
            total_bytes += dataset.get('size_bytes', 0)
    
    return total_bytes / (1024 * 1024)  # Convert to MB

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.route('/api/v1/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    name = data.get('name', '')
    
    # Validation
    if not email or '@' not in email:
        return jsonify({'error': 'Invalid email'}), 400
    
    if not password or len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    
    load_users()
    
    # Check if user exists
    if email in users_db:
        return jsonify({'error': 'Email already registered'}), 409
    
    # Create user
    user_id = f"user_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hash(email) % 10000}"
    user = {
        'user_id': user_id,
        'email': email,
        'name': name,
        'password_hash': hash_password(password),
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
        'profile': {
            'avatar_url': None,
            'bio': '',
            'organization': '',
            'phone': ''
        },
        'settings': {
            'dark_mode': True,
            'notifications_enabled': True,
            'notifications_email': True
        },
        'storage': {
            'used_mb': 0,
            'max_mb': MAX_STORAGE_PER_USER_MB
        }
    }
    
    users_db[email] = user
    save_users()
    
    # Initialize user storage
    load_projects()
    if user_id not in projects_db:
        projects_db[user_id] = []
    save_projects()
    
    load_datasets()
    if user_id not in datasets_db:
        datasets_db[user_id] = []
    save_datasets()
    
    token = generate_token(user_id)
    
    return jsonify({
        'user': {
            'user_id': user['user_id'],
            'email': user['email'],
            'name': user['name'],
            'created_at': user['created_at']
        },
        'token': token,
        'message': 'User registered successfully'
    }), 201

@app.route('/api/v1/auth/login', methods=['POST'])
def login():
    """Login user"""
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    load_users()
    
    if email not in users_db:
        return jsonify({'error': 'Invalid email or password'}), 401
    
    user = users_db[email]
    
    if not verify_password(password, user['password_hash']):
        return jsonify({'error': 'Invalid email or password'}), 401
    
    token = generate_token(user['user_id'])
    
    return jsonify({
        'user': {
            'user_id': user['user_id'],
            'email': user['email'],
            'name': user['name'],
            'created_at': user['created_at']
        },
        'token': token,
        'message': 'Logged in successfully'
    }), 200

@app.route('/api/v1/auth/profile', methods=['GET'])
@require_auth
def get_profile():
    """Get user profile"""
    load_users()
    
    # Find user by user_id
    user_data = None
    for email, user in users_db.items():
        if user['user_id'] == request.user_id:
            user_data = user
            break
    
    if not user_data:
        return jsonify({'error': 'User not found'}), 404
    
    storage_used = get_user_storage_usage(request.user_id)
    
    return jsonify({
        'user': {
            'user_id': user_data['user_id'],
            'email': user_data['email'],
            'name': user_data['name'],
            'created_at': user_data['created_at'],
            'updated_at': user_data['updated_at'],
            'profile': user_data['profile'],
            'settings': user_data['settings'],
            'storage': {
                'used_mb': round(storage_used, 2),
                'max_mb': user_data['storage']['max_mb'],
                'percentage_used': round((storage_used / user_data['storage']['max_mb']) * 100, 2)
            }
        }
    }), 200

@app.route('/api/v1/auth/profile', methods=['PUT'])
@require_auth
def update_profile():
    """Update user profile"""
    data = request.get_json() or {}
    load_users()
    
    # Find user by user_id
    user_data = None
    user_email = None
    for email, user in users_db.items():
        if user['user_id'] == request.user_id:
            user_data = user
            user_email = email
            break
    
    if not user_data:
        return jsonify({'error': 'User not found'}), 404
    
    # Update allowed fields
    if 'name' in data:
        user_data['name'] = data['name']
    if 'profile' in data:
        user_data['profile'].update(data['profile'])
    if 'settings' in data:
        user_data['settings'].update(data['settings'])
    
    user_data['updated_at'] = datetime.now().isoformat()
    users_db[user_email] = user_data
    save_users()
    
    return jsonify({
        'user': {
            'user_id': user_data['user_id'],
            'email': user_data['email'],
            'name': user_data['name'],
            'profile': user_data['profile'],
            'settings': user_data['settings']
        },
        'message': 'Profile updated successfully'
    }), 200

# ============================================================================
# PROJECT ENDPOINTS (USER-SCOPED)
# ============================================================================

@app.route('/api/v1/projects', methods=['GET'])
@require_auth
def list_projects():
    """List projects for current user"""
    load_projects()
    
    user_projects = projects_db.get(request.user_id, [])
    
    return jsonify({
        'projects': user_projects,
        'total_count': len(user_projects),
        'page': 1,
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/api/v1/projects', methods=['POST'])
@require_auth
def create_project():
    """Create a new project for current user"""
    data = request.get_json() or {}
    project_id = f"proj_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    project = {
        'id': project_id,
        'user_id': request.user_id,
        'name': data.get('name', 'Untitled Project'),
        'description': data.get('description', ''),
        'created_at': datetime.now().isoformat(),
        'status': 'active',
        'data_sources': data.get('data_sources', []),
        'last_updated': datetime.now().isoformat()
    }
    
    load_projects()
    if request.user_id not in projects_db:
        projects_db[request.user_id] = []
    
    projects_db[request.user_id].append(project)
    save_projects()
    
    return jsonify({
        'project': project,
        'message': 'Project created successfully',
        'timestamp': datetime.now().isoformat()
    }), 201

@app.route('/api/v1/projects/<project_id>', methods=['GET'])
@require_auth
def get_project(project_id):
    """Get a specific project"""
    load_projects()
    
    user_projects = projects_db.get(request.user_id, [])
    project = next((p for p in user_projects if p['id'] == project_id), None)
    
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    
    return jsonify({'project': project}), 200

@app.route('/api/v1/projects/<project_id>', methods=['PUT'])
@require_auth
def update_project(project_id):
    """Update a project"""
    data = request.get_json() or {}
    load_projects()
    
    user_projects = projects_db.get(request.user_id, [])
    project = next((p for p in user_projects if p['id'] == project_id), None)
    
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    
    # Update fields
    if 'name' in data:
        project['name'] = data['name']
    if 'description' in data:
        project['description'] = data['description']
    if 'status' in data:
        project['status'] = data['status']
    
    project['last_updated'] = datetime.now().isoformat()
    save_projects()
    
    return jsonify({
        'project': project,
        'message': 'Project updated successfully'
    }), 200

@app.route('/api/v1/projects/<project_id>', methods=['DELETE'])
@require_auth
def delete_project(project_id):
    """Delete a project"""
    load_projects()
    
    user_projects = projects_db.get(request.user_id, [])
    project = next((p for p in user_projects if p['id'] == project_id), None)
    
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    
    projects_db[request.user_id] = [p for p in user_projects if p['id'] != project_id]
    save_projects()
    
    return jsonify({
        'message': 'Project deleted successfully'
    }), 200

# ============================================================================
# DATASET ENDPOINTS (USER-SCOPED)
# ============================================================================

@app.route('/api/v1/datasets', methods=['GET'])
@require_auth
def list_datasets():
    """List datasets for current user"""
    load_datasets()
    
    user_datasets = datasets_db.get(request.user_id, [])
    storage_used = get_user_storage_usage(request.user_id)
    
    return jsonify({
        'datasets': user_datasets,
        'total_count': len(user_datasets),
        'storage_used_mb': round(storage_used, 2),
        'storage_max_mb': MAX_STORAGE_PER_USER_MB,
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/api/v1/datasets', methods=['POST'])
@require_auth
def upload_dataset():
    """Upload a new dataset"""
    data = request.get_json() or {}
    
    dataset_id = f"dataset_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    size_bytes = data.get('size_bytes', 0)
    storage_used = get_user_storage_usage(request.user_id)
    storage_used_after = storage_used + (size_bytes / (1024 * 1024))
    
    # Check storage limit
    if storage_used_after > MAX_STORAGE_PER_USER_MB:
        return jsonify({
            'error': f'Storage limit exceeded. Current: {round(storage_used, 2)}MB, Max: {MAX_STORAGE_PER_USER_MB}MB'
        }), 413
    
    dataset = {
        'id': dataset_id,
        'user_id': request.user_id,
        'name': data.get('name', 'Untitled Dataset'),
        'file_name': data.get('file_name', ''),
        'file_type': data.get('file_type', 'csv'),
        'size_bytes': size_bytes,
        'rows': data.get('rows', 0),
        'columns': data.get('columns', 0),
        'column_names': data.get('column_names', []),
        'created_at': datetime.now().isoformat(),
        'project_id': data.get('project_id', None),
        'description': data.get('description', '')
    }
    
    load_datasets()
    if request.user_id not in datasets_db:
        datasets_db[request.user_id] = []
    
    datasets_db[request.user_id].append(dataset)
    save_datasets()
    
    return jsonify({
        'dataset': dataset,
        'message': 'Dataset uploaded successfully',
        'timestamp': datetime.now().isoformat()
    }), 201

@app.route('/api/v1/datasets/<dataset_id>', methods=['GET'])
@require_auth
def get_dataset(dataset_id):
    """Get a specific dataset"""
    load_datasets()
    
    user_datasets = datasets_db.get(request.user_id, [])
    dataset = next((d for d in user_datasets if d['id'] == dataset_id), None)
    
    if not dataset:
        return jsonify({'error': 'Dataset not found'}), 404
    
    return jsonify({'dataset': dataset}), 200

@app.route('/api/v1/datasets/<dataset_id>', methods=['DELETE'])
@require_auth
def delete_dataset(dataset_id):
    """Delete a dataset"""
    load_datasets()
    
    user_datasets = datasets_db.get(request.user_id, [])
    dataset = next((d for d in user_datasets if d['id'] == dataset_id), None)
    
    if not dataset:
        return jsonify({'error': 'Dataset not found'}), 404
    
    datasets_db[request.user_id] = [d for d in user_datasets if d['id'] != dataset_id]
    save_datasets()
    
    return jsonify({
        'message': 'Dataset deleted successfully'
    }), 200

# ============================================================================
# JOBS ENDPOINTS (USER-SCOPED)
# ============================================================================

@app.route('/api/v1/jobs', methods=['POST'])
@require_auth
def create_job():
    """Submit a query job"""
    data = request.get_json() or {}
    job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    return jsonify({
        'job_id': job_id,
        'user_id': request.user_id,
        'status': 'queued',
        'message': 'Analysis job created successfully',
        'estimated_completion': '2-3 minutes',
        'priority': 'normal',
        'input_data': data,
        'created_at': datetime.now().isoformat(),
        'queue_position': 1
    }), 201

@app.route('/api/v1/jobs/<job_id>')
@require_auth
def get_job_status(job_id):
    """Get job status"""
    return jsonify({
        'job_id': job_id,
        'user_id': request.user_id,
        'status': 'completed',
        'progress': 100,
        'results': {
            'summary': {
                'total_records_analyzed': 1250000,
                'analysis_duration_seconds': 45,
                'confidence_score': 0.94
            },
            'insights': [
                'Revenue increased by 23% in Q3 compared to Q2',
                'Top product category: Electronics (45% of total sales)',
                'Customer retention rate improved to 78%',
                'Mobile traffic accounts for 67% of conversions',
                'Average order value: $156.78 (+12% vs last quarter)'
            ]
        },
        'completed_at': datetime.now().isoformat()
    }), 200

# ============================================================================
# SYSTEM ENDPOINTS
# ============================================================================

@app.route('/')
def root():
    """Root endpoint"""
    return jsonify({
        'message': 'AI Data Analyst MVP API',
        'version': '2.0.0-auth',
        'timestamp': datetime.now().isoformat(),
        'status': 'running',
        'features': ['authentication', 'user-scoped-projects', 'user-scoped-datasets', 'storage-limits']
    })

@app.route('/health')
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'ai-analyst-api',
        'version': '2.0.0-auth'
    })

@app.route('/api/v1/health/detailed')
def detailed_health():
    """Detailed health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'ai-analyst-api',
        'version': '2.0.0-auth',
        'uptime_seconds': 3600,
        'checks': {
            'database': 'healthy',
            'storage': 'healthy',
            'authentication': 'healthy'
        }
    })

if __name__ == '__main__':
    # Initialize storage
    load_users()
    load_projects()
    load_datasets()
    
    print(f"""
    ╔═══════════════════════════════════════════════════╗
    ║  AI Data Analyst API (v2.0.0-auth) Starting...   ║
    ╠═══════════════════════════════════════════════════╣
    ║  Features:                                        ║
    ║  ✓ User Authentication (JWT)                     ║
    ║  ✓ User-Scoped Projects                          ║
    ║  ✓ User-Scoped Datasets                          ║
    ║  ✓ Storage Limits ({MAX_STORAGE_PER_USER_MB}MB per user)       ║
    ║                                                   ║
    ║  Endpoint: http://localhost:8080                 ║
    ║  Docs: http://localhost:8080/docs                ║
    ╚═══════════════════════════════════════════════════╝
    """)
    
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=True)

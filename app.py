from flask import Flask, render_template, request, redirect, url_for, flash
import pymysql
import boto3
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
# Flask-Login requires a secret key to sign session cookies securely
app.secret_key = 'super_secret_corporate_key' 

# --- FLASK LOGIN SETUP ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Redirects users here if they try to access protected pages

# Simple User class for Flask-Login
class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    if user_id == "admin":
        return User(id="admin")
    return None

# --- DATABASE & S3 SETUP ---
def get_db_connection():
    return pymysql.connect(
        host="portal-db.cg58646wiyye.us-east-1.rds.amazonaws.com",
        user="admin",
        password="Ankitha2005",
        database="portal_db",
        autocommit=True
    )

# Run standard schema migration safely inside a temporary context wrapper
try:
    init_db = get_db_connection()
    init_cursor = init_db.cursor()
    init_cursor.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id INT AUTO_INCREMENT PRIMARY KEY,
        title VARCHAR(255),
        content TEXT
    )
    """)
    init_db.close()
except Exception as e:
    print(f"Database setup warning: {e}")

S3_BUCKET = "corp-portal-documents-ananya"
s3 = boto3.client('s3')


# --- AUTHENTICATION ROUTES (MEMBER 4) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Simple security check for our admin user
        if username == 'admin' and password == 'admin123':
            user = User(id="admin")
            login_user(user)
            return redirect('/')
        else:
            return "Invalid credentials. Please try again."
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')


# --- CORE DASHBOARD ENVIRONMENT ---
@app.route('/')
@login_required
def home():
    # 1. Count total blog posts safely using a short-lived execution block
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(*) FROM posts")
        total_posts = cursor.fetchone()[0]
        db.close()
    except Exception as e:
        total_posts = 0

    # 2. Count total files uploaded to S3
    try:
        response = s3.list_objects_v2(Bucket=S3_BUCKET)
        total_docs = len(response.get('Contents', []))
    except Exception as e:
        total_docs = 0 

    # Renders the clean dashboard design interface with current data metrics
    return render_template('dashboard.html', total_posts=total_posts, total_docs=total_docs)


# --- BLOG ROUTES (MEMBER 2) ---
@app.route('/blog')
@login_required
def view_blog():
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM posts")
        posts = cursor.fetchall()
        db.close()
    except Exception as e:
        posts = []

    # Map database row tuples into structured list arrays for the design layout
    formatted_posts = []
    for post in posts:
        formatted_posts.append({
            'title': post[1],
            'content': post[2]
        })

    return render_template('blog.html', posts=formatted_posts)

@app.route('/create', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        try:
            db = get_db_connection()
            cursor = db.cursor()
            title = request.form['title']
            content = request.form['content']

            sql = "INSERT INTO posts(title, content) VALUES(%s, %s)"
            cursor.execute(sql, (title, content))
            db.close()
        except Exception as e:
            print(f"Error saving entry: {e}")

        return redirect('/blog')

    return render_template('create_post.html')


# --- DOCUMENT ROUTES (MEMBER 3) ---
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename != '':
            s3.upload_fileobj(file, S3_BUCKET, file.filename)
            return redirect('/documents')
    return render_template('upload.html')

@app.route('/documents')
@login_required 
def documents():
    try:
        response = s3.list_objects_v2(Bucket=S3_BUCKET)
    except Exception as e:
        response = {}

    files = []
    if 'Contents' in response:
        for obj in response['Contents']:
            filename = obj['Key']
            
            # Generate pre-signed security delivery URL
            url = s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': S3_BUCKET, 'Key': filename},
                ExpiresIn=3600
            )
            
            files.append({
                'name': filename,
                'url': url
            })
    return render_template('documents.html', files=files)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

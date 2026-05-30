from flask import Flask, render_template, request, redirect, url_for
import pymysql
import boto3
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user

app = Flask(__name__)
app.secret_key = 'super_secret_corporate_key' 

# --- FLASK LOGIN SETUP ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

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

# Database table initialization
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
    print(f"Database connection setup fallback trace: {e}")

S3_BUCKET = "corp-portal-documents-ananya"
s3 = boto3.client('s3')

# --- AUTHENTICATION ROUTES ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == 'admin123':
            user = User(id="admin")
            login_user(user)
            return redirect(url_for('home'))
        else:
            return "Invalid credentials. Please try again."
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- CORE DASHBOARD SYSTEM ---
@app.route('/')
@login_required
def home():
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(*) FROM posts")
        total_posts = cursor.fetchone()[0]
        db.close()
    except Exception:
        total_posts = 0

    try:
        response = s3.list_objects_v2(Bucket=S3_BUCKET)
        total_docs = len(response.get('Contents', []))
    except Exception:
        total_docs = 0 

    return render_template('dashboard.html', total_posts=total_posts, total_docs=total_docs)

# --- BLOG ROUTES ---
@app.route('/blog')
@login_required
def view_blog():
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("SELECT id, title, content FROM posts ORDER BY id DESC")
        posts = cursor.fetchall()
        db.close()
    except Exception:
        posts = []

    formatted_posts = []
    for post in posts:
        formatted_posts.append({
            'id': post[0],
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
            cursor.execute("INSERT INTO posts(title, content) VALUES(%s, %s)", (title, content))
            db.close()
        except Exception as e:
            print(f"Error publishing post entry: {e}")
        return redirect(url_for('view_blog'))
    return render_template('create_post.html')

# --- DOCUMENT ROUTES ---
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename != '':
            s3.upload_fileobj(file, S3_BUCKET, file.filename)
            return redirect(url_for('view_documents'))
    return render_template('upload.html')

@app.route('/documents')
@login_required 
def view_documents():
    try:
        response = s3.list_objects_v2(Bucket=S3_BUCKET)
    except Exception:
        response = {}

    files = []
    if 'Contents' in response:
        for obj in response['Contents']:
            filename = obj['Key']
            url = s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': S3_BUCKET, 'Key': filename},
                ExpiresIn=3600
            )
            files.append({'name': filename, 'url': url})
            
    return render_template('documents.html', files=files)
# --- TEMPORARY CLEANUP ROUTE ---
@app.route('/delete-test-blogs-secret')
@login_required
def delete_test_blogs():
    try:
        db = get_db_connection()
        cursor = db.cursor()
        # This deletes ALL posts from the table
        cursor.execute("TRUNCATE TABLE posts")
        db.close()
        return "<h1>Success! All testing blogs have been permanently deleted.</h1><p><a href='/blog'>Go back to Blog</a></p>"
    except Exception as e:
        return f"<h1>Error clearing database:</h1><p>{e}</p>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

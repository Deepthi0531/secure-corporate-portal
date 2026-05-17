from flask import Flask, render_template, request, redirect, flash
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
    # For now, we are using a simple hardcoded admin. 
    # In a real app, you would query the RDS database here.
    if user_id == "admin":
        return User(id="admin")
    return None

# --- DATABASE & S3 SETUP ---
db = pymysql.connect(
    host="portal-db.cg58646wiyye.us-east-1.rds.amazonaws.com",
    user="admin",
    password="Ankitha2005", # Note: In production, never hardcode passwords!
    database="portal_db"
)

cursor = db.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS posts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255),
    content TEXT
)
""")
db.commit()

S3_BUCKET="corp-portal-documents-ananya"
s3=boto3.client('s3')


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
            return redirect('/admin')
        else:
            return "Invalid credentials. Please try again."
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')

@app.route('/admin')
@login_required
def admin_dashboard():
    # 1. Count total blog posts from RDS
    cursor.execute("SELECT COUNT(*) FROM posts")
    total_posts = cursor.fetchone()[0]

    # 2. Count total files uploaded to S3
    try:
        response = s3.list_objects_v2(Bucket=S3_BUCKET)
        total_files = len(response.get('Contents', []))
    except Exception as e:
        total_files = 0 # If bucket is empty or errors out

    return render_template('admin_dashboard.html', total_posts=total_posts, total_files=total_files)


# --- BLOG ROUTES (MEMBER 2) ---
@app.route('/')
def home():
    cursor.execute("SELECT * FROM posts")
    posts = cursor.fetchall()
    return render_template('blog.html', posts=posts)

@app.route('/create', methods=['GET', 'POST'])
@login_required # Secured!
def create_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        sql = "INSERT INTO posts(title, content) VALUES(%s, %s)"
        cursor.execute(sql, (title, content))
        db.commit()
        return redirect('/')
    return render_template('create_post.html')


# --- DOCUMENT ROUTES (MEMBER 3) ---
@app.route('/upload-page')
@login_required # Secured!
def upload_page():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
@login_required # Secured!
def upload_file():
    file = request.files['file']
    if file:
        s3.upload_fileobj(file, S3_BUCKET, file.filename)
    return redirect('/documents')

@app.route('/documents')
@login_required 
def documents():
    response = s3.list_objects_v2(Bucket=S3_BUCKET)
    files = []
    if 'Contents' in response:
        for obj in response['Contents']:
            filename = obj['Key']
            
            # --- THE SECURITY FIX: Generate a Pre-Signed URL ---
            # This URL will grant temporary access for 1 hour (3600 seconds)
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
from flask import Flask, render_template, request, redirect
import pymysql
import boto3

app = Flask(__name__)

db = pymysql.connect(
    host="portal-db.cg58646wiyye.us-east-1.rds.amazonaws.com",
    user="admin",
    password="Ankitha2005",
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
@app.route('/')
def home():
    cursor.execute("SELECT * FROM posts")
    posts = cursor.fetchall()
    return render_template('blog.html', posts=posts)

@app.route('/create', methods=['GET', 'POST'])
def create_post():

    if request.method == 'POST':

        title = request.form['title']
        content = request.form['content']

        sql = "INSERT INTO posts(title, content) VALUES(%s, %s)"
        cursor.execute(sql, (title, content))
        db.commit()

        return redirect('/')

    return render_template('create_post.html')
@app.route('/upload-page')
def upload_page():
    return render_template('upload.html')


@app.route('/upload', methods=['POST'])
def upload_file():

    file = request.files['file']

    if file:
        s3.upload_fileobj(file, S3_BUCKET, file.filename)

    return redirect('/documents')


@app.route('/documents')
def documents():

    response = s3.list_objects_v2(Bucket=S3_BUCKET)

    files = []

    if 'Contents' in response:

        for obj in response['Contents']:

            filename = obj['Key']

            url = f"https://{S3_BUCKET}.s3.amazonaws.com/{filename}"

            files.append({
                'name': filename,
                'url': url
            })

    return render_template('documents.html', files=files)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

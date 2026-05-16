from flask import Flask, render_template, request, redirect
import pymysql

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

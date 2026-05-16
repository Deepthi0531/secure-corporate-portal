from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return "<h1>Secure Corporate Portal Running</h1><p>Welcome to the baseline infrastructure.</p>"

if __name__ == '__main__':
    # Run on 0.0.0.0 so it is accessible publicly via the EC2 IP
    app.run(host='0.0.0.0', port=5000, debug=True)

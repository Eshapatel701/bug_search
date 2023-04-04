import mysql.connector
from flask import Flask, render_template, request, url_for, flash, redirect
from werkzeug.exceptions import abort

def get_db_connection():
    mydb = mysql.connector.connect(
        host = "localhost",
        user = "root",
        password = "142857",
        database = "BugSearch"
    )
    # conn.row_factory = sqlite3.Row
    return mydb

app = Flask(__name__)
app.config['SECRE_KEY'] = 'your secret key'

@app.route('/')
def login_home():
    return render_template('login_home.html')

@app.route('/user_home')
def user_home():
    return render_template('user_home.html')

@app.route('/signup', methods=('GET', 'POST'))
def signup():
    if request.method == 'POST':
        email_id = request.form['email_id']
        username = request.form['username']
        passcode = request.form['passcode']
        if not email_id:
            flash('Email address is required!')
        elif not username:
            flash('Username is required!')
        elif not passcode:
            flash('Please set password!')
        else:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('INSERT INTO Users (email_id, username, passcode) VALUES (%s, %s, %s)',
                            (email_id, username, passcode))
            conn.commit()
            conn.close()
            return redirect(url_for('user_home'))
    return render_template('signup.html')
        


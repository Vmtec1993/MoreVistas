from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)

# Initializing a simple database
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    # Create Villas table
    cursor.execute('''CREATE TABLE IF NOT EXISTS villas 
                      (id INTEGER PRIMARY KEY, name TEXT, price REAL, description TEXT)''')
    # Create Bookings table
    cursor.execute('''CREATE TABLE IF NOT EXISTS bookings 
                      (id INTEGER PRIMARY KEY, villa_id INTEGER, guest_name TEXT, date TEXT)''')
    
    # Add dummy data if empty
    cursor.execute("SELECT COUNT(*) FROM villas")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO villas (name, price, description) VALUES (?, ?, ?)", 
                       ("Ocean View Paradise", 250.0, "A stunning 3-bedroom villa by the sea."))
        cursor.execute("INSERT INTO villas (name, price, description) VALUES (?, ?, ?)", 
                       ("Mountain Retreat", 180.0, "Cozy cabin style villa in the heart of the woods."))
    conn.commit()
    conn.close()

@app.route('/')
def index():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM villas")
    villas = cursor.fetchall()
    conn.close()
    return render_template('index.html', villas=villas)

@app.route('/book/<int:villa_id>', methods=['GET', 'POST'])
def book(villa_id):
    if request.method == 'POST':
        guest_name = request.form['guest_name']
        date = request.form['date']
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO bookings (villa_id, guest_name, date) VALUES (?, ?, ?)", 
                       (villa_id, guest_name, date))
        conn.commit()
        conn.close()
        return redirect('/')
    
    return render_template('book.html', villa_id=villa_id)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)

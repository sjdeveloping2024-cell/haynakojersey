"""
Pick-A-Book Library System
Flask backend using MySQL (mysql-connector-python)
"""

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify
)
import mysql.connector
from mysql.connector import Error as MySQLError
from datetime import datetime, timedelta
from functools import wraps
from config import DB_CONFIG
import serial
import serial.tools.list_ports
import threading
import time

app = Flask(__name__)
app.secret_key = 'pick-a-book-secret-key-2024'


# ─── ARDUINO SERIAL ──────────────────────────────────────────────────────────

arduino = None          # global serial connection
_serial_lock = threading.Lock()

def find_arduino_port():
    """Auto-detect the Arduino COM/tty port."""
    ports = serial.tools.list_ports.comports()
    for p in ports:
        desc = (p.description or '').lower()
        if any(k in desc for k in ('arduino', 'ch340', 'ch341', 'cp210', 'ftdi', 'usb serial')):
            return p.device
    # fallback: return first available port
    return ports[0].device if ports else None

def init_arduino():
    """Connect to Arduino on startup (non-fatal if not found)."""
    global arduino
    port = find_arduino_port()
    if not port:
        print('[Arduino] No Arduino port found — LCD disabled.')
        return
    try:
        arduino = serial.Serial(port, 9600, timeout=2)
        time.sleep(2)          # wait for Arduino reset after Serial open
        print(f'[Arduino] Connected on {port}')
        lcd_send('Pick-A-Book', 'System Ready')
    except Exception as e:
        print(f'[Arduino] Could not open {port}: {e}')
        arduino = None

def lcd_send(line1: str, line2: str = ''):
    """
    Send a 2-line message to Arduino over Serial.
    Protocol:  LINE1|LINE2\n   (max 16 chars each, truncated)
    """
    global arduino
    if arduino is None or not arduino.is_open:
        return
    msg = f'{line1[:16]}|{line2[:16]}\n'
    with _serial_lock:
        try:
            arduino.write(msg.encode('utf-8'))
        except Exception as e:
            print(f'[Arduino] Write error: {e}')


# ─── DATABASE HELPERS ────────────────────────────────────────────────────────

def get_db():
    """Open a new MySQL connection and return (conn, cursor) tuple."""
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)   # rows come back as dicts
    return conn, cursor


def close_db(conn, cursor):
    if cursor:
        cursor.close()
    if conn and conn.is_connected():
        conn.close()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated


# ─── LANDING ─────────────────────────────────────────────────────────────────

@app.route('/')
def landing_page():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')


# ─── AUTH ─────────────────────────────────────────────────────────────────────

@app.route('/login')
def login_page():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('LogIn.html')


@app.route('/login', methods=['POST'])
def login_process():
    email    = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()

    # ── Step 1: empty field checks ───────────────────────────
    if not email or not password:
        flash('Both email and password are required.')
        return redirect(url_for('login_page'))

    # ── Step 2: basic email format check ─────────────────────
    if '@' not in email or '.' not in email.split('@')[-1]:
        flash('Please enter a valid email address.')
        return redirect(url_for('login_page'))

    conn, cursor = get_db()
    try:
        # ── Step 3: check if email is registered at all ──────
        cursor.execute(
            'SELECT * FROM librarians WHERE email = %s', (email,)
        )
        user = cursor.fetchone()
        if not user:
            flash('No account found with that email. Please register first.')
            lcd_send('Login Failed', 'Not registered')
            return redirect(url_for('login_page'))

        # ── Step 4: verify password ──────────────────────────
        if user['password'] != password:
            flash('Incorrect password. Please try again.')
            lcd_send('Login Failed', 'Wrong password')
            return redirect(url_for('login_page'))

        # ── Step 5: all good — create session ────────────────
        session['user_id']   = user['id']
        session['user_name'] = user['full_name']
        session['role']      = user['role']
        lcd_send('Login OK', user['full_name'][:16])
        return redirect(url_for('dashboard'))

    finally:
        close_db(conn, cursor)


@app.route('/register')
def registration_page():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('Register.html')


@app.route('/register', methods=['POST'])
def register_process():
    name     = request.form.get('name', '').strip()
    email    = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()

    # ── Step 1: empty field checks ───────────────────────────
    if not name or not email or not password:
        flash('All fields (name, email, password) are required.')
        return redirect(url_for('registration_page'))

    # ── Step 2: name length ───────────────────────────────────
    if len(name) < 2:
        flash('Full name must be at least 2 characters.')
        return redirect(url_for('registration_page'))

    # ── Step 3: basic email format ────────────────────────────
    if '@' not in email or '.' not in email.split('@')[-1]:
        flash('Please enter a valid email address.')
        return redirect(url_for('registration_page'))

    # ── Step 4: password length ───────────────────────────────
    if len(password) < 6:
        flash('Password must be at least 6 characters.')
        return redirect(url_for('registration_page'))

    conn, cursor = get_db()
    try:
        # ── Step 5: check if email is already taken ───────────
        cursor.execute(
            'SELECT id FROM librarians WHERE email = %s', (email,)
        )
        if cursor.fetchone():
            flash('That email is already registered. Please log in instead.')
            return redirect(url_for('registration_page'))

        # ── Step 6: all good — insert new librarian ──────────
        cursor.execute(
            'INSERT INTO librarians (full_name, email, password) VALUES (%s, %s, %s)',
            (name, email, password)
        )
        conn.commit()
        flash('Account created successfully! You can now log in.')
        lcd_send('Registered!', name[:16])
        return redirect(url_for('login_page'))

    except MySQLError as e:
        flash(f'Database error: {e.msg}')
        return redirect(url_for('registration_page'))
    finally:
        close_db(conn, cursor)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))


# ─── DASHBOARD ───────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    conn, cursor = get_db()
    try:
        cursor.execute('SELECT COALESCE(SUM(quantity), 0) AS total FROM books')
        total_books = cursor.fetchone()['total']

        cursor.execute('SELECT COUNT(*) AS total FROM students')
        total_students = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) AS total FROM borrows WHERE status = 'borrowed'")
        borrowed_books = cursor.fetchone()['total']

        cursor.execute('SELECT COALESCE(SUM(available), 0) AS total FROM books')
        available_books = cursor.fetchone()['total']

        cursor.execute('''
            SELECT b.id,
                   s.student_id  AS student_code,
                   s.full_name   AS student_name,
                   bk.title      AS book_title,
                   b.borrow_date,
                   b.due_date
            FROM   borrows b
            JOIN   students s  ON b.student_id = s.id
            JOIN   books    bk ON b.book_id    = bk.id
            WHERE  b.status = 'borrowed'
            ORDER  BY b.borrow_date DESC
        ''')
        recent_borrowed = cursor.fetchall()

        # Convert date objects to strings for Jinja2
        for row in recent_borrowed:
            for k in ('borrow_date', 'due_date'):
                if row.get(k) and not isinstance(row[k], str):
                    row[k] = row[k].strftime('%Y-%m-%d')

        return render_template('index.html',
            total_books     = total_books,
            total_students  = total_students,
            borrowed_books  = borrowed_books,
            available_books = available_books,
            recent_borrowed = recent_borrowed,
        )
    finally:
        close_db(conn, cursor)


# ─── BORROW ──────────────────────────────────────────────────────────────────

@app.route('/borrow', methods=['POST'])
@login_required
def borrow_book():
    student_code = request.form['student_id']
    book_id      = request.form['book_id']
    conn, cursor = get_db()
    try:
        cursor.execute('SELECT * FROM students WHERE student_id = %s', (student_code,))
        student = cursor.fetchone()
        if not student:
            flash('Student not found.')
            lcd_send('Borrow Error', 'Student N/A')
            return redirect(url_for('dashboard'))

        cursor.execute(
            'SELECT * FROM books WHERE id = %s AND available > 0', (book_id,)
        )
        book = cursor.fetchone()
        if not book:
            flash('Book not available or does not exist.')
            lcd_send('Borrow Error', 'Book N/A')
            return redirect(url_for('dashboard'))

        today    = datetime.now().strftime('%Y-%m-%d')
        due_date = (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')

        cursor.execute(
            'INSERT INTO borrows (student_id, book_id, borrow_date, due_date) VALUES (%s, %s, %s, %s)',
            (student['id'], book_id, today, due_date)
        )
        cursor.execute(
            'UPDATE books SET available = available - 1 WHERE id = %s', (book_id,)
        )
        conn.commit()
        flash('Book borrowed successfully!')
        short_title = book['title'][:16]
        short_name  = student['full_name'].split()[0][:16]
        lcd_send(f'Borrowed:', f'{short_name} - {short_title}'[:16])
        return redirect(url_for('dashboard'))
    finally:
        close_db(conn, cursor)


# ─── RETURN ──────────────────────────────────────────────────────────────────

@app.route('/return', methods=['POST'])
@login_required
def return_book():
    borrow_id = request.form['borrow_id']
    conn, cursor = get_db()
    try:
        cursor.execute('SELECT * FROM borrows WHERE id = %s', (borrow_id,))
        borrow = cursor.fetchone()
        if borrow and borrow['status'] == 'borrowed':
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute(
                "UPDATE borrows SET status = 'returned', return_date = %s WHERE id = %s",
                (today, borrow_id)
            )
            cursor.execute(
                'UPDATE books SET available = available + 1 WHERE id = %s',
                (borrow['book_id'],)
            )
            conn.commit()
            flash('Book returned successfully!')
            # fetch book title for LCD
            cursor.execute('SELECT title FROM books WHERE id = %s', (borrow['book_id'],))
            bk = cursor.fetchone()
            book_title = bk['title'][:16] if bk else 'Book'
            lcd_send('Returned OK!', book_title)
        else:
            flash('Invalid return request.')
            lcd_send('Return Error', 'Already returned')
        return redirect(url_for('dashboard'))
    finally:
        close_db(conn, cursor)


# ─── SEARCH STUDENT (AJAX) ───────────────────────────────────────────────────

@app.route('/search_student', methods=['POST'])
@login_required
def search_student():
    data = request.get_json()
    name = data.get('name', '')
    conn, cursor = get_db()
    try:
        cursor.execute('''
            SELECT s.student_id,
                   s.full_name,
                   bk.title    AS book_title,
                   b.due_date,
                   b.id        AS borrow_id
            FROM   borrows  b
            JOIN   students s  ON b.student_id = s.id
            JOIN   books    bk ON b.book_id    = bk.id
            WHERE  s.full_name LIKE %s
              AND  b.status = 'borrowed'
        ''', (f'%{name}%',))
        results = cursor.fetchall()
        # Serialise date objects
        for r in results:
            if r.get('due_date') and not isinstance(r['due_date'], str):
                r['due_date'] = r['due_date'].strftime('%Y-%m-%d')
        return jsonify({'students': results})
    finally:
        close_db(conn, cursor)


# ─── BOOKS ────────────────────────────────────────────────────────────────────

@app.route('/books')
@login_required
def books_page():
    conn, cursor = get_db()
    try:
        cursor.execute('''
            SELECT *,
                   CASE WHEN available > 0 THEN 'Available' ELSE 'Unavailable' END AS status
            FROM   books
            ORDER  BY id DESC
        ''')
        books = cursor.fetchall()
        return render_template('books.html', books=books)
    finally:
        close_db(conn, cursor)


@app.route('/add_book', methods=['POST'])
@login_required
def add_book():
    title    = request.form['title']
    author   = request.form['author']
    isbn     = request.form.get('isbn', '')
    category = request.form.get('category', '')
    quantity = int(request.form.get('quantity', 1))
    conn, cursor = get_db()
    try:
        cursor.execute(
            'INSERT INTO books (title, author, isbn, category, quantity, available) VALUES (%s, %s, %s, %s, %s, %s)',
            (title, author, isbn, category, quantity, quantity)
        )
        conn.commit()
        flash('Book added successfully!')
        return redirect(url_for('books_page'))
    finally:
        close_db(conn, cursor)


@app.route('/delete_book', methods=['POST'])
@login_required
def delete_book():
    book_id = request.form['book_id']
    conn, cursor = get_db()
    try:
        cursor.execute(
            "UPDATE borrows SET status = 'returned' WHERE book_id = %s AND status = 'borrowed'",
            (book_id,)
        )
        cursor.execute('DELETE FROM books WHERE id = %s', (book_id,))
        conn.commit()
        flash('Book deleted.')
        return redirect(url_for('books_page'))
    finally:
        close_db(conn, cursor)


# ─── STUDENTS ─────────────────────────────────────────────────────────────────

@app.route('/students')
@login_required
def students_page():
    search_query = request.args.get('search', '')
    conn, cursor = get_db()
    try:
        if search_query:
            cursor.execute(
                '''SELECT * FROM students
                   WHERE full_name  LIKE %s
                      OR student_id LIKE %s
                      OR email      LIKE %s
                   ORDER BY id DESC''',
                (f'%{search_query}%', f'%{search_query}%', f'%{search_query}%')
            )
        else:
            cursor.execute('SELECT * FROM students ORDER BY id DESC')
        students = cursor.fetchall()
        return render_template('Student.html', students=students, search_query=search_query)
    finally:
        close_db(conn, cursor)


@app.route('/add_student', methods=['POST'])
@login_required
def add_student():
    full_name  = request.form['full_name']
    student_id = request.form['student_id']
    email      = request.form.get('email', '')
    course     = request.form.get('course', '')
    year_level = request.form.get('year_level') or None
    conn, cursor = get_db()
    try:
        cursor.execute(
            'INSERT INTO students (full_name, student_id, email, course, year_level) VALUES (%s, %s, %s, %s, %s)',
            (full_name, student_id, email, course, year_level)
        )
        conn.commit()
        flash('Student added successfully!')
    except MySQLError as e:
        if e.errno == 1062:
            flash('Student ID already exists.')
        else:
            flash(f'Database error: {e.msg}')
    finally:
        close_db(conn, cursor)
    return redirect(url_for('students_page'))


@app.route('/delete_student', methods=['POST'])
@login_required
def delete_student():
    student_db_id = request.form['student_id']
    conn, cursor = get_db()
    try:
        cursor.execute('DELETE FROM borrows  WHERE student_id = %s', (student_db_id,))
        cursor.execute('DELETE FROM students WHERE id         = %s', (student_db_id,))
        conn.commit()
        flash('Student deleted.')
        return redirect(url_for('students_page'))
    finally:
        close_db(conn, cursor)


# ─── PROFILE ──────────────────────────────────────────────────────────────────

@app.route('/profile')
@login_required
def profile_page():
    conn, cursor = get_db()
    try:
        cursor.execute('SELECT * FROM librarians WHERE id = %s', (session['user_id'],))
        user = cursor.fetchone()

        cursor.execute('''
            SELECT s.full_name AS student_name,
                   bk.title,
                   b.borrow_date,
                   b.status
            FROM   borrows  b
            JOIN   students s  ON b.student_id = s.id
            JOIN   books    bk ON b.book_id    = bk.id
            ORDER  BY b.borrow_date DESC
            LIMIT  10
        ''')
        borrowed = cursor.fetchall()
        for row in borrowed:
            if row.get('borrow_date') and not isinstance(row['borrow_date'], str):
                row['borrow_date'] = row['borrow_date'].strftime('%Y-%m-%d')

        return render_template('Profile.html', user=user, borrowed=borrowed)
    finally:
        close_db(conn, cursor)


# ─── ABOUT ────────────────────────────────────────────────────────────────────

@app.route('/about')
@login_required
def about_page():
    return render_template('about.html')


# ─── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    init_arduino()
    app.run(debug=True)

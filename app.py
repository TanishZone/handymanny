from flask import Flask, render_template, request, redirect, session

import sqlite3

app = Flask(__name__)
app.secret_key = "handymanny_secret"

SKILLS = [
    "AC Technician","Accountant","Actor","Advertising Specialist","Agriculture Worker",
    "Animator","App Developer","Architect","Artist","Auto Mechanic",
    "Baker","Barber","Beautician","Blacksmith","Blog Writer",
    "Bricklayer","Business Consultant",
    "Carpenter","Caterer","Chef","Civil Engineer","Cleaner","Content Writer","Courier",
    "Data Analyst","Data Entry Operator","Delivery Boy","Dentist","Designer","Digital Marketer","Driver",
    "Electrician","Electronics Repair","Event Planner",
    "Farmer","Fashion Designer","Fitness Trainer","Florist",
    "Gardener","Graphic Designer",
    "Hair Stylist","Handyman","Home Tutor","House Cleaner",
    "Interior Designer","IT Support",
    "Jeweler","Journalist",
    "Lab Technician","Language Translator","Lawyer","Lecturer",
    "Machine Operator","Makeup Artist","Mason","Mechanic","Mobile Repair","Musician",
    "Nurse",
    "Painter","Photographer","Photocopier Technician","Physiotherapist","Plumber","Police Trainer",
    "Receptionist","Repair Technician",
    "Sales Executive","Security Guard","Shopkeeper","Social Media Manager","Software Developer",
    "Tailor","Taxi Driver","Teacher","Technician","Tour Guide",
    "Video Editor",
    "Waiter","Web Developer","Welder","Writer",
    "Yoga Trainer"
]


# Login Page
@app.route('/')
def login():
    return render_template('login.html')

# Signup Page
@app.route('/signup')
def signup():
    return render_template('signup.html')

# Handle Signup
@app.route('/signup_user', methods=['POST'])
def signup_user():
    email = request.form['email']
    full_name = request.form['full_name']
    password = request.form['password']
    import hashlib
    password = hashlib.sha256(password.encode()).hexdigest()

    conn = sqlite3.connect('database.db')
    import datetime

    date = datetime.datetime.now().strftime("%Y-%m-%d")
    existing = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()

    if existing:
        return "user already exists"
    conn.execute("""
    INSERT INTO users (email, password, full_name, member_since)
    VALUES (?, ?, ?, ?)
    """, (email, password, full_name, date))
    conn.commit()
    conn.close()

    session['user'] = email
    return redirect('/home')

# Handle Login
@app.route('/login_user', methods=['POST'])
def login_user():
    email = request.form['email']
    password = request.form['password']
    import hashlib
    password = hashlib.sha256(password.encode()).hexdigest()

    conn = sqlite3.connect('database.db')
    user = conn.execute("SELECT * FROM users WHERE email=? AND password=?",
                        (email, password)).fetchone()
    conn.close()

    if user:
        session['user'] = email  # ✅ store user
        return redirect('/home')
    else:
        return "Invalid user or Password"

# Home Page
@app.route('/home')
def home():
    if 'user' not in session:
        return redirect('/')

    email = session['user']

    conn = sqlite3.connect('database.db')
    data = conn.execute("SELECT full_name FROM users WHERE email=?", (email,)).fetchone()
    conn.close()

    name = data[0] if data else email

    conn = sqlite3.connect('database.db')
    count = conn.execute("SELECT COUNT(*) FROM messages WHERE receiver=?",
                         (email,)).fetchone()[0]
    conn.close()

    return render_template('home.html', username=name, msg_count=count)

@app.route('/offer')
def offer():
    if 'user' not in session:
        return redirect('/')
    return render_template('offer.html', skills=SKILLS)

@app.route('/hire', methods=['GET', 'POST'])
def hire():
    conn = sqlite3.connect('database.db')

    if request.method == 'POST':
        search = request.form.get('search', '')
        exp = request.form.get('exp_filter')

        services = conn.execute(
            "SELECT * FROM services WHERE skill LIKE ?",
            ('%' + search + '%',)
        ).fetchall()

        if exp:
            services = [s for s in services if s[9] == exp]

    else:
        services = conn.execute("SELECT * FROM services").fetchall()

    # Calculate average ratings
    service_list = []
    services = sorted(services, key=lambda x: x[0], reverse=True)

    for service in services:
        email = service[1]

        user_data = conn.execute(
            "SELECT full_name FROM users WHERE email=?", 
            (email,)
        ).fetchone()

        name = user_data[0] if user_data else email

        # new fields from services table

        phone = service[3]
        gender = service[4]
        dob = service[5]
        age = service[6]
        address = service[7]
        skill = service[8]  
        experience = service[9]
        about = service[10]
        verified = service[12]
        tasks = service[-1] if service[-1] is not None else 0

        data = conn.execute("""
        SELECT AVG(rating), COUNT(rating)
        FROM ratings WHERE service_id=?
        """, (service[0],)).fetchone()

        avg = round(data[0], 1) if data[0] else "No rating"
        count = data[1]

        service_list.append({
            "id": service[0],
            "name": name,
            "email": email,
            "phone": phone,
            "gender": gender,
            "age": age,
            "address": address,
            "skill": skill,
            "experience": experience,
            "about": about,
            "verified": verified,
            "rating": avg,
            "count": count,
            "tasks": tasks,
            "popularity": "High"
        })

    conn.close()
    return render_template('hire.html', services=service_list, skills=SKILLS)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

@app.route('/rate/<int:service_id>', methods=['POST'])
def rate(service_id):
    if 'user' not in session:
        return redirect('/')

    rating = request.form['rating']
    user = session['user']

    conn = sqlite3.connect('database.db')

    # Insert or update rating
    conn.execute("""
    INSERT INTO ratings (service_id, user, rating)
    VALUES (?, ?, ?)
    ON CONFLICT(service_id, user)
    DO UPDATE SET rating=excluded.rating
    """, (service_id, user, rating))

    conn.commit()
    conn.close()

    return redirect('/hire')

@app.route('/contact/<int:service_id>', methods=['POST'])
def contact(service_id):
    if 'user' not in session:
        return redirect('/')

    message = request.form['message']
    sender = session['user']

    conn = sqlite3.connect('database.db')
    conn.execute("INSERT INTO contacts (service_id, sender, message) VALUES (?, ?, ?)",
                 (service_id, sender, message))
    conn.commit()
    conn.close()

    return redirect('/hire')

@app.route('/chat/<receiver>', methods=['GET', 'POST'])
def chat(receiver):
    if 'user' not in session:
        return redirect('/')

    sender = session['user']
    conn = sqlite3.connect('database.db')

    # USER LIST
    users = conn.execute("""
    SELECT DISTINCT 
    CASE 
        WHEN sender = ? THEN receiver 
        ELSE sender 
    END as chat_user
    FROM messages
    WHERE sender = ? OR receiver = ?
    """, (sender, sender, sender)).fetchall()

    user_list = []
    for u in users:
        email = u[0]
        if email == sender:
            continue

        data = conn.execute(
            "SELECT full_name FROM users WHERE email=?",
            (email,)
        ).fetchone()

        name = data[0] if data else email
        user_list.append({"name": name, "email": email})

    # SEND MESSAGE (AJAX)
    if request.method == 'POST':
        msg = request.form['message']

        conn.execute(
            "INSERT INTO messages (sender, receiver, message) VALUES (?, ?, ?)",
            (sender, receiver, msg)
        )
        conn.commit()
        conn.close()

        return ("", 204)

    # GET CHAT DATA
    chats = conn.execute("""
    SELECT * FROM (
        SELECT id, sender, receiver, message, 'msg' as type FROM messages 
        WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?)

        UNION ALL

        SELECT id, client, worker, 'Hire Request', 'hire' FROM hires
        WHERE ((client=? AND worker=?) OR (client=? AND worker=?))
        AND status='pending'
    )
    ORDER BY id
    """, (sender, receiver, receiver, sender, sender, receiver, receiver, sender)).fetchall()

    # WORKER INFO
    worker = conn.execute("""
    SELECT skill, experience FROM services WHERE user=?
    """, (receiver,)).fetchone()

    # SERVICE ID (⚠️ MOVED ABOVE close)
    service_data = conn.execute(
        "SELECT id FROM services WHERE user=?",
        (receiver,)
    ).fetchone()

    service_id = service_data[0] if service_data else None

    # CHECK CLIENT
    is_client = True if sender != receiver else False

    # NOW CLOSE (ONLY HERE ✅)
    conn.close()

    return render_template(
        'chat.html',
        chats=chats,
        receiver=receiver,
        users=user_list,
        worker={
            "skill": worker[0] if worker else "",
            "experience": worker[1] if worker else "",
            "rating": 0
        },
        is_client=is_client,
        service_id=service_id
    )

@app.route('/inbox')
def inbox():
    if 'user' not in session:
        return redirect('/')

    user = session['user']

    conn = sqlite3.connect('database.db')

    users = conn.execute("""
        SELECT DISTINCT 
        CASE 
            WHEN sender = ? THEN receiver 
            ELSE sender 
        END as chat_user
        FROM messages
        WHERE sender = ? OR receiver = ?
    """, (user, user, user)).fetchall()

    # remove None or self
    final_users = []

    for u in users:
        email = u[0]

        if email == user:
            continue

        data = conn.execute(
            "SELECT full_name FROM users WHERE email=?",
            (email,)
        ).fetchone()

        name = data[0] if data else email
        final_users.append({
            "name": name,
            "email": email
        })

    conn.close()

    return render_template('inbox.html', users=final_users)

@app.route('/profile')
def profile():
    if 'user' not in session:
        return redirect('/')

    email = session['user']

    conn = sqlite3.connect('database.db')
    data = conn.execute("SELECT full_name FROM users WHERE email=?", (email,)).fetchone()

    name = data[0] if data else email

    services = conn.execute(
        "SELECT * FROM services WHERE user=?", 
        (email,)
    ).fetchall()

    conn.close()

    return render_template('profile.html', username=name, services=services)

@app.route('/delete_service/<int:id>')
def delete_service(id):
    if 'user' not in session:
        return redirect('/')
    user = session['user']

    conn = sqlite3.connect('database.db')
    conn.execute(
        "DELETE FROM services WHERE id=? AND user=?",
        (id, user)
    )
    conn.commit()
    conn.close()

    return redirect('/profile')

@app.route('/add_service', methods=['POST'])
def add_service():
    if 'user' not in session:
        return redirect('/')

    email = session['user']

    full_name = request.form['full_name']
    phone = request.form['phone']
    gender = request.form['gender']
    dob = request.form['dob']
    age = request.form['age']
    address = request.form['address']
    skill = request.form['skill']
    experience = request.form['experience']
    about = request.form['about']

    cert_id = request.form.get('cert_id')
    cert_name = request.form.get('cert_name', '')
    cert_org = request.form.get('cert_org', '')
    cert_link = request.form.get('cert_link')

    has_cert = request.form.get('has_cert')

    # 🔥 STRICT VALIDATION
    if has_cert == "Yes":
        if not cert_id or not cert_name or not cert_org or not cert_link:
            return "All certificate fields are required"

    verified = 1 if (cert_id and cert_name and cert_org and cert_link) else 0

    conn = sqlite3.connect('database.db')
    conn.execute("""
    INSERT INTO services (
        user, full_name, phone, gender, dob, age, address,
        skill, experience, about,
        photo, verified, cert_id, cert_name, cert_org, cert_link
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        email, full_name, phone, gender, dob, age, address,
        skill, experience, about,
        None, verified, cert_id, cert_name, cert_org, cert_link
    ))
    
    conn.commit()
    conn.close()

    return redirect('/home')

@app.route('/edit_verification/<int:id>', methods=['GET', 'POST'])
def edit_verification(id):
    if 'user' not in session:
        return redirect('/')

    conn = sqlite3.connect('database.db')

    if request.method == 'POST':
        cert_id = request.form['cert_id']
        cert_name = request.form.get('cert_name')
        cert_org = request.form.get('cert_org')
        cert_link = request.form['cert_link']

        verified = 1 if (cert_id and cert_name and cert_org and cert_link) else 0

        conn.execute("""
        UPDATE services
        SET cert_id=?, cert_name=?, cert_org=?, cert_link=?, verified=?
        WHERE id=?
        """, (cert_id, cert_name, cert_org, cert_link, verified, id))

        conn.commit()
        conn.close()
        return redirect('/profile')

    service = conn.execute("SELECT * FROM services WHERE id=?", (id,)).fetchone()
    conn.close()

    return render_template('edit_verification.html', service=service)

@app.route('/hire_request/<int:service_id>', methods=['POST'])
def hire_request(service_id):
    if 'user' not in session:
        return redirect('/')

    client = session['user']

    conn = sqlite3.connect('database.db')

    worker = conn.execute(
        "SELECT user FROM services WHERE id=?", 
        (service_id,)
    ).fetchone()[0]

    # ❗ FIXED ORDER
    if client == worker:
        conn.close()
        return redirect('/hire')

    existing = conn.execute("""
    SELECT * FROM hires 
    WHERE client=? AND worker=? AND status='pending'
    """, (client, worker)).fetchone()

    if existing:
        conn.close()
        return redirect('/hire')

    conn.execute("""
    INSERT INTO hires (service_id, client, worker, status)
    VALUES (?, ?, ?, ?)
    """, (service_id, client, worker, "pending"))

    conn.commit()
    conn.close()

    return redirect('/hire')

@app.route('/requests')
def requests():
    if 'user' not in session:
        return redirect('/')

    user = session['user']

    conn = sqlite3.connect('database.db')
    reqs = conn.execute("""
    SELECT * FROM hires WHERE worker=? AND status='pending'
    """, (user,)).fetchall()

    conn.close()

    return render_template('requests.html', requests=reqs)

@app.route('/accept/<int:id>')
def accept(id):
    if 'user' not in session:
        return redirect('/')

    user = session['user']

    conn = sqlite3.connect('database.db')
    conn.execute("""
    UPDATE hires 
    SET status='accepted' 
    WHERE id=? AND worker=?
    """, (id, user))
    conn.commit()
    conn.close()
    
    return redirect('/requests')

@app.route('/reject/<int:id>')
def reject(id):
    if 'user' not in session:
        return redirect('/')

    user = session['user']

    conn = sqlite3.connect('database.db')
    conn.execute("""
    UPDATE hires 
    SET status='rejected' 
    WHERE id=? AND worker=?
    """, (id, user))
    conn.commit()
    conn.close()

    return redirect('/requests')

@app.route('/connections')
def connections():
    if 'user' not in session:
        return redirect('/')

    user = session['user']

    conn = sqlite3.connect('database.db')

    raw = conn.execute("""
    SELECT * FROM hires 
    WHERE (client=? OR worker=?) AND status='accepted'
    """, (user, user)).fetchall()

    data = []

    for r in raw:
        service_id = r[1]
        client_email = r[2]
        worker_email = r[3]
        completed = r[5]

        # skill
        skill_data = conn.execute(
            "SELECT skill FROM services WHERE id=?",
            (service_id,)
        ).fetchone()
        skill = skill_data[0] if skill_data else ""

        # names
        client_data = conn.execute(
            "SELECT full_name FROM users WHERE email=?", 
            (client_email,)
        ).fetchone()

        worker_data = conn.execute(
            "SELECT full_name FROM users WHERE email=?", 
            (worker_email,)
        ).fetchone()

        client_name = client_data[0] if client_data else client_email
        worker_name = worker_data[0] if worker_data else worker_email

        # 🔥 CHECK IF REVIEW ALREADY GIVEN
        review = conn.execute("""
        SELECT * FROM reviews 
        WHERE hire_id=? AND client=?
        """, (r[0], user)).fetchone()

        reviewed = True if review else False

        data.append({
            "id": r[0],
            "skill": skill,
            "client": client_name,
            "worker": worker_name,
            "client_email": client_email,
            "worker_email": worker_email,
            "completed": completed,
            "reviewed": reviewed
        })

    conn.close()

    return render_template('connections.html', data=data)

@app.route('/complete/<int:id>')
def complete(id):
    if 'user' not in session:
        return redirect('/')

    user = session['user']

    conn = sqlite3.connect('database.db')

    # get worker email
    worker = conn.execute("""
    SELECT worker FROM hires WHERE id=?
    """, (id,)).fetchone()[0]

    # mark complete
    conn.execute("""
    UPDATE hires SET completed=1 
    WHERE id=? AND (client=? OR worker=?)
    """, (id, user, user))

    # increase task count
    conn.execute("UPDATE services SET tasks = COALESCE(tasks,0) + 1 WHERE user=?", (worker,))

    conn.commit()
    conn.close()

    return redirect('/connections')

@app.route('/cancel/<int:id>')
def cancel(id):
    if 'user' not in session:
        return redirect('/')

    user = session['user']

    conn = sqlite3.connect('database.db')
    conn.execute("""
    UPDATE hires 
    SET status='cancelled' 
    WHERE id=? AND (client=? OR worker=?)
    """, (id, user, user))
    conn.commit()
    conn.close()

    return redirect('/connections')

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user' not in session:
        return redirect('/')

    email = session['user']
    conn = sqlite3.connect('database.db')

    if request.method == 'POST':
        phone = request.form['phone']
        address = request.form['address']

        conn.execute("""
        UPDATE services
        SET phone=?, address=?
        WHERE user=?
        """, (phone, address, email))

        conn.commit()
        conn.close()
        return redirect('/profile')

    # GET
    service = conn.execute(
        "SELECT * FROM services WHERE user=?", 
        (email,)
    ).fetchone()

    conn.close()

    return render_template('edit_profile.html', service=service)

@app.route('/review/<int:id>', methods=['POST'])
def review(id):
    if 'user' not in session:
        return redirect('/')

    client = session['user']
    rating = request.form['rating']
    feedback = request.form['feedback']

    conn = sqlite3.connect('database.db')

    worker = conn.execute(
        "SELECT worker FROM hires WHERE id=?", 
        (id,)
    ).fetchone()[0]

    # prevent multiple ratings
    existing = conn.execute("""
    SELECT * FROM reviews WHERE hire_id=? AND client=?
    """, (id, client)).fetchone()

    if existing:
        conn.close()
        return redirect('/connections')
    
    conn.execute("""
    INSERT INTO reviews (hire_id, worker, client, rating, feedback)
    VALUES (?, ?, ?, ?, ?)
    """, (id, worker, client, rating, feedback))

    service_id = conn.execute(
        "SELECT service_id FROM hires WHERE id=?",
        (id,)
    ).fetchone()[0]

    conn.execute("""
    INSERT INTO ratings (service_id, user, rating)
    VALUES (?, ?, ?)
    """, (service_id, client, rating))

    conn.commit()
    conn.close()

    return redirect('/connections')

@app.route('/get_messages/<receiver>')
def get_messages(receiver):
    from flask import jsonify

    if 'user' not in session:
        return jsonify({"chats": []})

    sender = session['user']

    conn = sqlite3.connect('database.db')

    chats = conn.execute("""
    SELECT * FROM messages 
    WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?)
    ORDER BY id
    """, (sender, receiver, receiver, sender)).fetchall()

    chat_list = []

    # normal messages
    for c in chats:
        chat_list.append({
            "id": c[0],
            "sender": c[1],
            "message": c[3],
            "time": c[4],
            "seen": c[5],
            "type": "msg"
        })

    # hire requests
    hires = conn.execute("""
    SELECT id, client, worker, status FROM hires
    WHERE ((client=? AND worker=?) OR (client=? AND worker=?))
    AND status='pending'
    """, (sender, receiver, receiver, sender)).fetchall()

    for h in hires:
        chat_list.append({
            "id": h[0],
            "sender": h[1],        # client
            "receiver": h[2],      # worker
            "message": "Hire Request",
            "type": "hire",
            "is_receiver": (h[2] == sender)   # ✅ KEY FIX
        })

    chat_list = sorted(chat_list, key=lambda x: x["id"])

    conn.execute("""
    UPDATE messages SET seen=1 
    WHERE receiver=? AND sender=?
    """, (sender, receiver))
    
    conn.commit()
    conn.close()
    
    return jsonify({"chats": chat_list})

@app.route('/edit_service/<int:id>', methods=['GET','POST'])
def edit_service(id):
    if 'user' not in session:
        return redirect('/')

    conn = sqlite3.connect('database.db')

    if request.method == 'POST':
        full_name = request.form['full_name']
        phone = request.form['phone']
        gender = request.form['gender']
        address = request.form['address']
        skill = request.form['skill']
        experience = request.form['experience']
        about = request.form['about']

        conn.execute("""
        UPDATE services 
        SET full_name=?, phone=?, gender=?, address=?, skill=?, experience=?, about=?
        WHERE id=?
        """, (full_name, phone, gender, address, skill, experience, about, id))
        conn.commit()
        conn.close()
        return redirect('/profile')

    service = conn.execute("SELECT * FROM services WHERE id=?", (id,)).fetchone()
    conn.close()

    return render_template('edit_service.html', service=service)

def init_db():
    conn = sqlite3.connect('database.db')

    conn.execute('''CREATE TABLE IF NOT EXISTS users
            (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            password TEXT,
            full_name TEXT,
            verified INTEGER DEFAULT 0,
            cert_id TEXT,
            cert_link TEXT,
            govt_verified TEXT,
            member_since TEXT
            )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS services
            (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            full_name TEXT,
            phone TEXT,
            gender TEXT,
            dob TEXT,
            age INTEGER,
            address TEXT,
            skill TEXT,
            experience TEXT,
            about TEXT,
            photo TEXT,
            verified INTEGER DEFAULT 0,
            cert_id TEXT,
            cert_name TEXT,
            cert_org TEXT,
            cert_link TEXT,
            govt_verified TEXT
            )''')
    
    conn.execute('''CREATE TABLE IF NOT EXISTS ratings
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_id INTEGER,
                user TEXT,
                rating INTEGER
            )''')
    
    conn.execute('''CREATE TABLE IF NOT EXISTS contacts
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
             service_id INTEGER,
             sender TEXT,
             message TEXT)''')
    
    conn.execute('''CREATE TABLE IF NOT EXISTS messages
            (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            receiver TEXT,
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            seen INTEGER DEFAULT 0
            )''')
    
    conn.execute('''CREATE TABLE IF NOT EXISTS hires
            (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_id INTEGER,
            client TEXT,
            worker TEXT,
            status TEXT,
            completed INTEGER DEFAULT 0
            )''')
    
    conn.execute('''CREATE TABLE IF NOT EXISTS reviews
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hire_id INTEGER,
                worker TEXT,
                client TEXT,
                rating INTEGER,
                feedback TEXT
            )''')

    columns = conn.execute("PRAGMA table_info(services)").fetchall()
    col_names = [c[1] for c in columns]

    if "tasks" not in col_names:
        conn.execute("ALTER TABLE services ADD COLUMN tasks INTEGER DEFAULT 0")

    conn.close()


init_db()

if __name__ == '__main__':
    import os

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
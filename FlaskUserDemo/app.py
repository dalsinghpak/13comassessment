import uuid, os, hashlib
from flask import Flask, request, render_template, redirect, url_for, session, abort, flash, jsonify
app = Flask(__name__)

# Register the setup page and import create_connection()
from utils import create_connection, setup
app.register_blueprint(setup)

@app.before_request
def restrict():
    restricted_pages = [
        'list_users',
        'view_user',
        'delete',
        'edit_user'
        ]
    if 'logged_in' not in session and request.endpoint in restricted_pages:
        return redirect('/login')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods={'GET', 'POST'})
def login():
    if request.method == 'POST':

        password = request.form['password']
        encrypted_password = hashlib.sha256(password.encode()).hexdigest()

        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM student WHERE email=%s AND password=%s"
                values = (
                    request.form['email'],
                    encrypted_password
                    )
                cursor.execute(sql, values)
                result = cursor.fetchone()
        if result:
             session['logged_in'] = True
             session['first_name'] = result['first_name']
             session['role'] = result['role']
             session['id'] = result['id']
             return redirect('/')
             flash("you finally got the password right")
        else:
             flash("looks like someone has memory loss")
             return redirect("/login")
    else:
        return render_template('login.html')
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

    

# TODO: Add a '/register' (add_user) route that uses INSERT
@app.route('/register', methods=['GET', 'POST'])
def add_user():

    if request.method == 'POST':

        password = request.form['password']
        encrypted_password = hashlib.sha256(password.encode()).hexdigest()

        if request.files['avatar'].filename:
            avatar_image = request.files["avatar"]
            ext = os.path.splitext(avatar_image.filename)[1]
            avatar_filename = str(uuid.uuid4())[:8] + ext
            avatar_image.save("static/images/" + avatar_filename)
        else:
            avatar_filename = None
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = """INSERT INTO student 
                (first_name, last_name, email, password, avatar)
                VALUES (%s, %s, %s, %s, %s)
                """
                values = (
                    request.form['first_name'],
                    request.form['last_name'],
                    request.form['email'],
                    encrypted_password,
                    avatar_filename
                    )
          
                try:
                    cursor.execute(sql, values)
                    connection.commit()
                except pymysql.err.IntegrityError:
                    flash('email already in use')
                    return redirect('/register')
                sql = "SELECT * FROM student WHERE email=%s AND password=%s"
                values = (
                    request.form['email'],
                    encrypted_password
                    )
                cursor.execute(sql, values)
                result = cursor.fetchone()
        if result:
             session['logged_in'] = True
             session['first_name'] = result['first_name']
             session['role'] = result['role']
             session['id'] = result['id']
             return redirect('/')
        return redirect('/', result=result)
    return render_template('users_add.html')



# TODO: Add a '/dashboard' (list_users) route that uses SELECT
@app.route('/dashboard')
def list_users():
    if session['role'] != 'admin':
        return abort(404)
    with create_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM users")
            result = cursor.fetchall()
    return render_template('users_list.html', result=result)

@app.route('/show')
def show():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM subjects")
            result = cursor.fetchall()
    return render_template('movie_add.html', result=result)


@app.route('/movieview')
def movie_view():
    if session['role'] != 'admin':
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = """SELECT student.first_name, subjects.Name FROM joining
    JOIN student ON joining.studentid = student.id
    JOIN subjects ON joining.subjectid = subjects.id WHERE studentid = %s"""
                values = (session['id'])
                cursor.execute(sql, values)
                result = cursor.fetchall()                                                                                                                                                                                                                                                                                                                                                                                    
        return render_template('movies_view.html', result=result)
    elif session['role'] == 'admin':
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = """SELECT student.first_name, subjects.`Name` FROM joining
    JOIN student ON joining.studentid = student.id
    JOIN subjects ON joining.subjectid = subjects.id"""
                values = ()
                cursor.execute(sql, values)
                result = cursor.fetchall() 


        return render_template('movies_view.html', result=result)

@app.route('/movieviewad')
def movie_viewad():
    if session['role'] != 'admin':
        return abort(404)
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = """SELECT users.first_name, movies.`name` FROM main_movie
JOIN users ON main_movie.personid = users.id
JOIN movies ON main_movie.movieid = movies.id WHERE personid = %s"""
            values = (session['id'])
            cursor.execute(sql, values)
            result = cursor.fetchall() 
    return render_template('movies_viewad.html', result=result)

# TODO: Add a '/profile' (view_user) route that uses SELECT
@app.route('/view')
def view_user():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = """SELECT * FROM users WHERE id=%s"""
            values = (request.args['id'])
            cursor.execute(sql, values)
            result = cursor.fetchone()
    return render_template('users_view.html', result=result)
# TODO: Add a '/delete_user' route that uses DELETE
@app.route('/delete')
def delete():
    if session['role'] != 'admin':
        return abort(404)
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = """DELETE FROM users WHERE id = %s"""
            values = (request.args['id'])
            cursor.execute(sql, values)
            connection.commit()
    return redirect('/dashboard')

@app.route('/add')
def add():

    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql =  """INSERT INTO joining 
                (studentid, subjectid)
                VALUES (%s, %s)
                """
            values = (session['id'], request.args['id']
                      )
            try:
                cursor.execute(sql, values)
                connection.commit()
            except pymysql.err.IntegrityError:
                flash('you already have this subject')
                return redirect('/add')
    flash('Movie Watched')
    return redirect('/')


# TODO: Add an '/edit_user' route that uses UPDATE
@app.route('/edit_user', methods=['GET', 'POST'])
def edit_user():
    if session['role'] != 'admin' and str(session['id']) != request.args['id']:
        return abort(404)
    if request.method == 'POST':
        if request.files['avatar'].filename:
            avatar_image = request.files["avatar"]
            ext = os.path.splitext(avatar_image.filename)[1]
            avatar_filename = str(uuid.uuid4())[:8] + ext
            avatar_image.save("static/images/" + avatar_filename)
            if request.form['old_avatar'] != 'None' :
                os.remove("static/images/" + request.form['old_avatar'])
        else:
            avatar_filename = request.form['old_avatar']

        with create_connection() as connection:
            with connection.cursor() as cursor:

                sql = """UPDATE users SET
                    first_name = %s,
                    last_name = %s,
                    email = %s,
                    password = %s,
                    avatar = %s
                    WHERE id = %s"""
                values = (
                    request.form['first_name'],
                    request.form['last_name'],
                    request.form['email'],
                    encrypted_password,
                    avatar_filename,
                    request.form['id']
                    
                )
                cursor.execute(sql, values)
                connection.commit()
        return redirect('/dashboard')
    else:
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM users WHERE id = %s"
                values = (request.args['id'])
                cursor.execute(sql, values)
                result = cursor.fetchone()
        return render_template('users_edit.html', result=result)

@app.route('/checkemail')
def check_email():
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM users WHERE email=%s"
                values = (
                    request.args['email']
                    )
                cursor.execute(sql, values)
                result = cursor.fetchone()
            if result:
                return jsonify({ 'status': 'Error' })
            else:
                return jsonify({ 'status': 'OK' })
    

if __name__ == '__main__':
    import os

    # This is required to allow flashing messages. We will cover this later.
    app.secret_key = os.urandom(32)

    HOST = os.environ.get('SERVER_HOST', 'localhost')
    try:
        PORT = int(os.environ.get('SERVER_PORT', '5555'))
    except ValueError:
        PORT = 5555
    app.run(HOST, PORT, debug=True)

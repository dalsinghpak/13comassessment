import uuid, os, hashlib, pymysql
from datetime import date, datetime
from flask import (
    Flask,
    request,
    render_template,
    redirect,
    url_for,
    session,
    abort,
    flash,
    jsonify,
)

app = Flask(__name__)

# Register the setup page and import create_connection()
from utils import create_connection, setup

app.register_blueprint(setup)

# setting up restricted pages
@app.before_request
def restrict():
    restricted_pages = ["list_users", "view_user", "delete", "edit_user"]
    if "logged_in" not in session and request.endpoint in restricted_pages:
        return redirect("/login")

# home
@app.route("/")
def home():
    return render_template("index.html")

# login to the website
@app.route("/login", methods={"GET", "POST"})
def login():
    if request.method == "POST":

        password = request.form["password"]
        encrypted_password = hashlib.sha256(password.encode()).hexdigest() # encrypts password

        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM users WHERE email=%s AND password=%s"
                values = (request.form["email"], encrypted_password)
                cursor.execute(sql, values)
                result = cursor.fetchone()
        if result:
            session["logged_in"] = True
            session["first_name"] = result["first_name"]
            session["role"] = result["role"]
            session["id"] = result["id"]
            return redirect("/")
            flash("you finally got the password right")
        else:
            flash("Incorrect Password")
            return redirect("/login")
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# allows the user to sign up
@app.route("/register", methods=["GET", "POST"])
def add_user():

    if request.method == "POST":
        # encrypts the password
        password = request.form["password"]
        encrypted_password = hashlib.sha256(password.encode()).hexdigest() 
        # for avatar image name
        if request.files["avatar"].filename:
            avatar_image = request.files["avatar"]
            ext = os.path.splitext(avatar_image.filename)[1]
            avatar_filename = str(uuid.uuid4())[:8] + ext
            avatar_image.save("static/images/" + avatar_filename)
        else:
            avatar_filename = None
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = """INSERT INTO users
                (first_name, last_name, email, password, avatar)
                VALUES (%s, %s, %s, %s, %s)
                """
                values = (
                    request.form["first_name"],
                    request.form["last_name"],
                    request.form["email"],
                    encrypted_password,
                    avatar_filename,
                )

                try:
                    cursor.execute(sql, values)
                    connection.commit()
                except pymysql.err.IntegrityError:
                    flash("email already in use")
                    return redirect("/register")
                sql = "SELECT * FROM users WHERE email=%s AND password=%s"
                values = (request.form["email"], encrypted_password)
                cursor.execute(sql, values)
                result = cursor.fetchone()
        # auto login for user after signing up
        if result:
            session["logged_in"] = True
            session["first_name"] = result["first_name"]
            session["role"] = result["role"]
            session["id"] = result["id"]
            return redirect("/")
        return redirect("/", result=result)
    return render_template("users_add.html")


# Admin Subject add
@app.route("/subject_add", methods=["GET", "POST"])
def subject_add():

    if request.method == "POST":
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = """INSERT INTO subjects
                (Name, Credits, Teacher, Summary, year_level)
                VALUES (%s, %s, %s, %s, %s)
                """
                values = (
                    request.form["subject_name"],
                    request.form["Credits"],
                    request.form["Teacher"],
                    request.form["Summary"],
                    request.form["year_level"],
                )

                try:
                    cursor.execute(sql, values)
                    connection.commit()
                # solves integrity error
                except pymysql.err.IntegrityError:
                    flash("Subject already added")
                    return redirect("/subject_add")
        flash("Subject added")
        return redirect("/")
    return render_template("admin_subject_add.html")


# list all users and all data
@app.route("/dashboard")
def list_users():
    if session["role"] != "admin":
        return abort(404)
    with create_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM users")
            result = cursor.fetchall()
    return render_template("users_list.html", result=result)

# allow the user to select an subject
@app.route("/subject_select")
def subject_select():
    # get todays date
    datenow = datetime.now() 
    # 1 second before midnight on that date
    duedate = datetime(2022, 12, 10, 23, 59, 59) 
    # start date
    startdate = datetime(2022, 7, 6)
    if datenow <= duedate and datenow >= startdate:
        with create_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM subjects")
                result = cursor.fetchall()
        print(result)
        return render_template("subject_add.html", result=result, years=({row['year_level'] for row in result}), faculties=({row['Faculty'] for row in result}))
    else:
        return render_template("selection_expired.html")


# Lets user view their subjects or admin view all users subjects
@app.route("/subject_view")
def subject_view():
    if session["role"] != "admin":
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = """SELECT joining.id, users.first_name, subjects.Name FROM joining
    JOIN users ON joining.usersid = users.id
    JOIN subjects ON joining.subjectid = subjects.id WHERE usersid = %s"""
                values = session["id"]
                cursor.execute(sql, values)
                result = cursor.fetchall()
                sql1 = """SELECT * FROM users WHERE id = %s"""
                values1 = session["id"]
                cursor.execute(sql1, values1)
                result1 = cursor.fetchone()
        return render_template("subject_view.html", result=result, result1=result1)

    elif session["role"] == "admin":
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = """SELECT users.first_name, subjects.`Name` FROM joining
    JOIN users ON joining.usersid = users.id
    JOIN subjects ON joining.subjectid = subjects.id"""
                values = ()
                cursor.execute(sql, values)
                result = cursor.fetchall()
        return render_template("subject_view.html", result=result)


# admin can filter students by subject
@app.route("/admin_subject_view")
def admin_subject_view():
    if session["role"] == "admin":
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = """SELECT joining.id, users.first_name, subjects.Name FROM joining
    JOIN users ON joining.usersid = users.id
    JOIN subjects ON joining.subjectid = subjects.id WHERE subjectid = %s"""
                values = request.args["id"]
                cursor.execute(sql, values)
                result = cursor.fetchall() 
                # need 2 sql querys to avoid tuple error
                sql1 = """SELECT * FROM subjects WHERE id = %s"""
                values1 = request.args["id"]
                cursor.execute(sql1, values1)
                result1 = cursor.fetchone()
        return render_template(
            "admin_subject_view.html", result=result, result1=result1
        )


# Lets admin view all subjects
@app.route("/admin_subject_list")
def admin_subject_list():
    if session["role"] == "admin":
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = """SELECT * FROM subjects"""
                values = ()
                cursor.execute(sql, values)
                result = cursor.fetchall()
        return render_template("admin_subject_list.html", result=result)


# Admin can see their subjects
@app.route("/subjectviewad")
def subject_viewad():
    if session["role"] != "admin":
        return abort(404)
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = """SELECT joining.id, users.first_name, subjects.Name FROM joining
    JOIN users ON joining.usersid = users.id
    JOIN subjects ON joining.subjectid = subjects.id WHERE usersid = %s"""
            values = session["id"]
            cursor.execute(sql, values)
            result = cursor.fetchall()
            sql1 = """SELECT * FROM users WHERE id = %s"""
            values1 = session["id"]
            cursor.execute(sql1, values1)
            result1 = cursor.fetchone()
    return render_template("subject_viewad.html", result=result, result1=result1)


# view profile this shows all details of the user
@app.route("/view")
def view_user():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = """SELECT joining.id, users.first_name, users.last_name, users.email, users.avatar , subjects.Name FROM joining
    JOIN users ON joining.usersid = users.id
    JOIN subjects ON joining.subjectid = subjects.id WHERE usersid = %s"""
            values = request.args["id"]
            cursor.execute(sql, values)
            result = cursor.fetchall()
            sql1 = """SELECT * FROM users WHERE users.id = %s"""
            values1 = request.args["id"]
            cursor.execute(sql1, values1)
            result1 = cursor.fetchone()
    return render_template("users_view.html", result=result, result1=result1)


# deleting subject and student from joing table
@app.route("/delete")
def delete():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = """DELETE FROM joining WHERE id = %s"""
            values = request.args["id"]
            cursor.execute(sql, values)
            connection.commit()
    return redirect("/")

# deletes user profile
@app.route("/delete_user")
def delete_user():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = """DELETE FROM users WHERE id = %s"""
            values = request.args["id"]
            cursor.execute(sql, values)
            connection.commit()
    return redirect("/")

# lets admin delete a subject
@app.route("/delete_subject")
def delete_subject():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = """DELETE FROM subjects WHERE id = %s"""
            values = request.args["id"]
            cursor.execute(sql, values)
            connection.commit()
    return redirect("/")


# users can add their subject
@app.route("/add")
def add():

    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = """INSERT INTO joining
                (usersid, subjectid)
                VALUES (%s, %s)
                """
            values = (session["id"], request.args["id"])
            try:
                cursor.execute(sql, values)
                connection.commit()
            except pymysql.err.IntegrityError:
                flash("you already have this subject")
                return redirect("/add")
    flash("Subject added")
    return redirect("/")


# lets user admin update student details
@app.route("/edit_user", methods=["GET", "POST"])
def edit_user():
    # checks whether admin is accessing
    if session["role"] != "admin" and str(session["id"]) != request.args["id"]: 
        return abort(404)
    if request.method == "POST":
        # for avatar image
        if request.files["avatar"].filename:
            avatar_image = request.files["avatar"]
            ext = os.path.splitext(avatar_image.filename)[1]
            avatar_filename = str(uuid.uuid4())[:8] + ext
            avatar_image.save("static/images/" + avatar_filename)
            if request.form["old_avatar"] != "None":
                os.remove("static/images/" + request.form["old_avatar"])
        else:
            avatar_filename = request.form["old_avatar"]
        with create_connection() as connection:
            with connection.cursor() as cursor:
                if request.form["password"]:
                    password = request.form["password"]
                    encrypted_password = hashlib.sha256(password.encode()).hexdigest()
                    sql = """UPDATE users SET
                    first_name = %s,
                    last_name = %s,
                    email = %s,
                    password = %s,
                    year_level = %s,
                    avatar = %s
                    WHERE id = %s"""
                    values = (
                        request.form["first_name"],
                        request.form["last_name"],
                        request.form["email"],
                        encrypted_password,
                        request.form["year_level"],
                        avatar_filename,
                        request.form["id"],
                    )
                    cursor.execute(sql, values)
                    connection.commit()
        return redirect("/dashboard")
    else:
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM users WHERE id = %s"
                values = request.args["id"]
                cursor.execute(sql, values)
                result = cursor.fetchone()
        return render_template("users_edit.html", result=result)


# Editing the subject
@app.route("/subject_edit", methods=["GET", "POST"])
def subject_edit():
    if session["role"] != "admin" and str(session["id"]) != request.args["id"]:
        return abort(404)
    else:
        if request.method == "POST":
            with create_connection() as connection:
                with connection.cursor() as cursor:
                    sql = """UPDATE subjects SET
                        Name = %s,
                        Credits = %s,
                        Teacher = %s,
                        Summary = %s,
                        year_level = %s
                        WHERE id = %s"""
                    values = (
                        request.form["Name"],
                        request.form["Credits"],
                        request.form["Teacher"],
                        request.form["Summary"],
                        request.form["year_level"],
                        request.form["id"],
                    )
                    cursor.execute(sql, values)
                    connection.commit()
            return redirect("/admin_subject_list")
        else:
            with create_connection() as connection:
                with connection.cursor() as cursor:
                    sql = "SELECT * FROM subjects WHERE id = %s"
                    values = request.args["id"]
                    cursor.execute(sql, values)
                    result = cursor.fetchone()
            return render_template("subject_edit.html", result=result)


# limiting subject selection and then adding the subject
@app.route("/subject_validate", methods=['POST'])
def vaildate():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = """SELECT users.first_name, subjects.Name FROM joining
    JOIN users ON joining.usersid = users.id
    JOIN subjects ON joining.subjectid = subjects.id WHERE usersid = %s"""
            values = session["id"]
            cursor.execute(sql, values)
            result = cursor.fetchall()

            print(request.form)
            # limit number
            if len(result) < 5:
                sql = """INSERT INTO joining
                        (usersid, subjectid)
                        VALUES (%s, %s)
                        """
                values = (session["id"], request.form["subject_id"])
                try:
                    cursor.execute(sql, values)
                    connection.commit()
                except pymysql.err.IntegrityError:
                    flash("you already have this subject")
            else:
                flash("Limit of 5 subjects reached.")
                return redirect("/show")
    flash("Selected")
    return redirect("/")

# checks weather email is already in use
@app.route("/checkemail")
def check_email():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM users WHERE email=%s"
            values = request.args["email"]
            cursor.execute(sql, values)
            result = cursor.fetchone()
        if result:
            return jsonify({"status": "Error"})
        else:
            return jsonify({"status": "OK"})


if __name__ == "__main__":
    import os

    # This is required to allow flashing messages.
    app.secret_key = os.urandom(32)

    HOST = os.environ.get("SERVER_HOST", "localhost")
    try:
        PORT = int(os.environ.get("SERVER_PORT", "5555"))
    except ValueError:
        PORT = 5555
    app.run(HOST, PORT, debug=True)

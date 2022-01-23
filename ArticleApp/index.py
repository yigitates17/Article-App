from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
import sqlite3
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps
from markupsafe import escape


class RegisterForm(Form):
    name = StringField("Name and Surname", validators=[validators.Length(min=4, max=25)])
    username = StringField("Username", validators=[validators.Length(min=5, max=35)])
    email = StringField("Email", validators=[validators.Email(message="Please enter a valid email address.")])
    password = PasswordField("Password:", validators=[
        validators.DataRequired(message="Please enter a password"),
        validators.EqualTo(fieldname="confirm", message="Your passwords don't match.")
    ])
    confirm = PasswordField("Confirm the password")


class LoginForm(Form):
    username = StringField("Username")
    password = PasswordField("Password")


class ArticleForm(Form):
    title = StringField("Title", validators=[
        validators.Length(message="Title can't be shorter than 3 and longer than 30 characters.", min=3, max=70)])
    content = TextAreaField("Content", validators=[
        validators.Length(message="You need to write more than 10 characters.", min=2)])


app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/register', methods=["GET", "POST"])
def register():
    register_form = RegisterForm(request.form)

    if request.method == "POST" and register_form.validate():

        blog_name = register_form.name.data
        blog_username = register_form.username.data
        blog_email = register_form.email.data
        blog_password = sha256_crypt.encrypt(register_form.password.data)

        con = sqlite3.connect('blog_database.db')
        cur = con.cursor()

        query = 'INSERT INTO blog_users(name, username, email, password) VALUES(?, ?, ?, ?)'

        cur.execute(query, (blog_name, blog_username, blog_email, blog_password))

        con.commit()
        con.close()

        flash("Signed up successfully.", "success")
        return redirect(url_for("login"))

    else:
        return render_template('register.html', form=register_form)


@app.route('/login', methods=["GET", "POST"])
def login():
    login_form = LoginForm(request.form)

    if request.method == "POST":
        username = login_form.username.data
        entered_password = login_form.password.data

        con = sqlite3.connect('blog_database.db')
        cur = con.cursor()

        find_user_execute = "SELECT * FROM blog_users WHERE username=?"

        select_user = cur.execute(find_user_execute, (username,))
        rows = cur.fetchall()

        if len(rows) > 0:

            real_password = rows[0][4]
            if sha256_crypt.verify(entered_password, real_password):

                flash("Logged in successfully.", "success")
                session["logged_in"] = True
                session["user_name"] = username

                return redirect(url_for('index', session=session))

            else:
                flash("Username or password is not correct.", "danger")
                return redirect(url_for('login'))
        else:
            flash("Username or password is not correct.", "danger")
            return redirect(url_for('login'))

        con.close()

    else:
        return render_template('login.html', login_form=login_form)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Login required to access this page.", "danger")
            return redirect(url_for('login'))

    return decorated_function


@app.route('/logout')
def logout():
    session.clear()
    flash("Successfully logged out.", "warning")
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    con = sqlite3.connect('blog_database.db')
    cur = con.cursor()

    query = 'SELECT * FROM articles WHERE author = ?'

    cur.execute(query, (session["user_name"],))
    rows = cur.fetchall()

    if len(rows) > 0:
        return render_template("dashboard.html", rows=rows)
        con.close()
    else:
        return render_template("dashboard.html")
        con.close()


@app.route('/articles')
def articles():
    con = sqlite3.connect('blog_database.db')
    cur = con.cursor()

    query = 'SELECT * FROM articles'

    cur.execute(query)
    rows = cur.fetchall()

    if len(rows) > 0:
        return render_template("articles.html", rows=rows)
        con.close()
    else:
        return render_template("articles.html")
        con.close()


@app.route('/articles/<string:article_no>', methods=['GET'])
def articles_pages(article_no):
    con = sqlite3.connect('blog_database.db')
    cur = con.cursor()

    query = 'SELECT * FROM articles where article_id = ?'

    cur.execute(query, (article_no,))
    article_exists = cur.fetchall()

    if len(article_exists) > 0:
        con.close()
        return render_template('article_pages.html', article=article_exists)

    else:
        con.close()
        return render_template("article_pages.html", article_no=article_no)


@app.route('/addarticle', methods=["POST", "GET"])
@login_required
def add_article():
    article = ArticleForm(request.form)

    if request.method == "POST" and article.validate():

        title = article.title.data
        content = article.content.data

        con = sqlite3.connect('blog_database.db')
        cur = con.cursor()

        query = 'INSERT INTO articles(title, author, content) VALUES(?, ?, ?)'

        cur.execute(query, (title, session["user_name"], content))

        con.commit()
        con.close()

        flash("Your article has been added successfully.", "success")
        return redirect(url_for("articles"))

    else:
        return render_template('addarticle.html', form=article)


@app.route('/delete/<string:id_article>')
@login_required
def article_delete(id_article):
    con = sqlite3.connect('blog_database.db')
    cur = con.cursor()

    select = 'SELECT * from articles where article_id = ?'
    delete = 'DELETE from articles where article_id = ?'

    cur.execute(select, (id_article,))
    article = cur.fetchall()

    if len(article) > 0:

        if session["user_name"] == article[0][2]:
            cur.execute(delete, (id_article,))
            flash(f"{article[0][1]} has been deleted.", "success")
            con.commit()
            con.close()
            return redirect(url_for('dashboard'))

        else:
            flash("You have no permission for this action.", "danger")
            con.close()
            return redirect(url_for('index'))
    else:
        flash("There is no article to delete in that index.", "danger")
        return redirect(url_for('index'))


@app.route('/edit/<string:id_article>', methods=["POST", "GET"])
@login_required
def article_update(id_article):
    con = sqlite3.connect('blog_database.db')
    cur = con.cursor()
    select = 'SELECT * from articles where article_id = ?'
    cur.execute(select, (id_article,))
    article = cur.fetchall()

    if request.method == "GET":

        if len(article) > 0:
            if session["user_name"] != article[0][2]:
                flash("You have no permission to edit that article.", "danger")
                con.close()
                return render_template('index.html')
            else:
                edit_form = ArticleForm()
                edit_form.title.data = article[0][1]
                edit_form.content.data = article[0][3]
                con.close()
                return render_template('edit_article.html', edit_form=edit_form, title=article[0][1])
        else:
            con.close()
            return render_template('edit_article.html', article_no=id_article)

    else:
        updated_form = ArticleForm(request.form)
        newContent = updated_form.content.data

        update = 'UPDATE articles set content = ? where article_id = ?'
        cur.execute(update, (newContent, id_article))
        flash(f"{article[0][1]} has been updated.", "success")
        con.commit()
        con.close()

        return redirect(url_for('dashboard'))


@app.route('/articles/search', methods=['GET', 'POST'])
def search():
    if request.method == "GET":
        return redirect(url_for('articles'))
    else:
        keyword = request.form.get("keyword")
        con = sqlite3.connect('blog_database.db')
        cur = con.cursor()
        search_query = "SELECT * from articles where title like '%" + keyword + "%'"
        cur.execute(search_query)
        find = cur.fetchall()

        if len(find) > 0:
            flash(f"We found {len(find)} results.", "success")
            return render_template('articles.html', rows=find)
        else:
            flash("We couldn't find the article you were looking for.", "warning")
            return redirect(url_for('articles'))


@app.route('/users')
def users():
    con = sqlite3.connect('blog_database.db')
    cur = con.cursor()
    select = 'SELECT id, username from blog_users'
    cur.execute(select)
    user_names = cur.fetchall()
    dict_list = []
    for user in user_names:
        if session["logged_in"] and session["user_name"] == user[1]:
            user_dict = {user: {"user_id": user[0], "username": user[1], "status": "Online"}}
        else:
            user_dict = {user: {"user_id": user[0], "username": user[1], "status": "Offline"}}
        dict_list.append(user_dict)

    return render_template('users.html', user_list=dict_list, user_names=user_names)


@app.route('/users/<string:userpage_id>')
@login_required
def user_page(userpage_id):
    return render_template('user_page.html', page_id=userpage_id)


if __name__ == '__main__':
    app.config['SECRET_KEY'] = "QWERTY123"
    app.run(debug=True)

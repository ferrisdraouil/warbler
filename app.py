import os

from flask import Flask, render_template, request, flash, redirect, session, g
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError

from forms import UserAddForm, LoginForm, MessageForm, EditProfileForm
from models import db, connect_db, User, Message, Like

# 'curr_user' is the key in session that we are looking for to see if user is logged in/ has access
CURR_USER_KEY = "curr_user"

app = Flask(__name__)

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config['SQLALCHEMY_DATABASE_URI'] = (os.environ.get(
    'DATABASE_URL', 'postgres:///warbler'))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")
toolbar = DebugToolbarExtension(app)

connect_db(app)
db.create_all()
##############################################################################
# User signup/login/logout


@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    # same as 'curr_user' in session
    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """

    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                image_url=form.image_url.data or User.image_url.default.arg,
            )
            db.session.commit()

        except IntegrityError as e:
            flash("Username already taken", 'danger')
            return render_template('users/signup.html', form=form)

        do_login(user)

        return redirect("/")

    else:
        return render_template('users/signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login."""

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data, form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)


@app.route('/logout')
def logout():
    """Handle logout of user."""

    # IMPLEMENT THIS
    session.clear()
    flash('You are logged out!')
    return redirect('/login')


##############################################################################
# General user routes:


@app.route('/users')
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    search = request.args.get('q')

    if not search:
        users = User.query.all()
    else:
        users = User.query.filter(User.username.like(f"%{search}%")).all()

    return render_template('users/index.html', users=users)


@app.route('/users/<int:user_id>')
def users_show(user_id):
    """Show user profile."""

    user = User.query.get_or_404(user_id)

    messages = Message.query.filter(Message.user_id == user_id).order_by(
        Message.timestamp.desc()).limit(100).all()
    # query all messages that followees have posted
    return render_template('users/show.html', user=user, messages=messages)


@app.route('/users/<int:user_id>/following')
def show_following(user_id):
    """Show list of people this user is following."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/following.html', user=user)


@app.route('/users/<int:user_id>/followers')
def users_followers(user_id):
    """Show list of followers of this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/followers.html', user=user)


@app.route('/users/follow/<int:follow_id>', methods=['POST'])
def add_follow(follow_id):
    """Add a follow for the currently-logged-in user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followee = User.query.get_or_404(follow_id)
    g.user.following.append(followee)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/stop-following/<int:follow_id>', methods=['POST'])
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followee = User.query.get(follow_id)
    g.user.following.remove(followee)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/<int:user_id>/profile', methods=["GET", "POST"])
def profile(user_id):
    """Update profile for current user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    # user = User.query.get_or_404(user_id)  # don't need to re-query
    form = EditProfileForm(obj=g.user)

    # POST
    if form.validate_on_submit():
        # check user password before continuing
        user = User.authenticate(g.user.username, form.password.data)

        if user:
            # process data and add to DB
            g.user.username = form.data.get('username')
            g.user.email = form.data.get('email')
            g.user.image_url = form.data.get('image_url')
            g.user.bio = form.data.get('bio')
            db.session.add(g.user)
            db.session.commit()
            return redirect(f'/users/{g.user.id}')
        elif not form.validate_on_submit():
            # didn't work
            form.username.errors = [""]  #
            return render_template('users/edit.html', form=form, user=g.user)

    # GET
    return render_template('users/edit.html', form=form, user=g.user)


@app.route('/users/delete', methods=["POST"])
def delete_user():
    """Delete user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    do_logout()

    db.session.delete(g.user)
    db.session.commit()

    return redirect("/signup")


##############################################################################
# Messages routes:


@app.route('/messages/new', methods=["GET", "POST"])
def messages_add():
    """Add a message:

    Show form if GET. If valid, update message and redirect to user page.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = MessageForm()

    if form.validate_on_submit():
        msg = Message(text=form.text.data)
        g.user.messages.append(msg)
        db.session.commit()

        return redirect(f"/users/{g.user.id}")

    return render_template('messages/new.html', form=form)


@app.route('/messages/<int:message_id>', methods=["GET"])
def messages_show(message_id):
    """Show a message."""

    msg = Message.query.get(message_id)
    return render_template('messages/show.html', message=msg)


@app.route('/messages/<int:message_id>/delete', methods=["POST"])
def messages_destroy(message_id):
    """Delete a message."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    msg = Message.query.get(message_id)
    db.session.delete(msg)
    db.session.commit()

    return redirect(f"/users/{g.user.id}")


##############################################################################
# Likes


@app.route('/<int:message_id>/like', methods=['POST'])
def add_like(message_id):

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    like = Like(liker_id=g.user.id, message_id=message_id)
    db.session.add(like)
    db.session.commit()

    return redirect(f'/users/{g.user.id}')


@app.route('/users/<int:user_id>/likes')
def show_user_likes(user_id):

    # messages_ids = {message_id for message in g.user.likes}

    user = User.query.get_or_404(user_id)
    message_ids = [like.message_id for like in user.likes]
    messages = Message.query.filter(Message.id.in_(message_ids)).all()

    return render_template('home.html', messages=messages)


##############################################################################
# Homepage and error pages


@app.route('/')
def homepage():
    """Show homepage:

    - anon users: no messages
    - logged in: 100 most recent messages of followees
    """

    if g.user:
        # collect all ids in a SET of those user is following PLUS user id
        all_ids = {leader.id for leader in g.user.following}.union({g.user.id})
        # filters all messages by all_ids
        messages = Message.query.order_by(Message.timestamp.desc()).filter(
            Message.user_id.in_(all_ids)).limit(100).all()

        # user_followees = user.following

        # snagging messages in order from the database;
        # user.messages won't be in order by default
        # query all messages that THE CURR USER has posted

        return render_template('home.html', messages=messages)

    else:
        return render_template('home-anon.html')


##############################################################################
# Turn off all caching in Flask
#   (useful for dev; in production, this kind of stuff is typically
#   handled elsewhere)
#
# https://stackoverflow.com/questions/34066804/disabling-caching-in-flask


@app.after_request
def add_header(req):
    """Add non-caching headers on every request."""

    req.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    req.headers["Pragma"] = "no-cache"
    req.headers["Expires"] = "0"
    req.headers['Cache-Control'] = 'public, max-age=0'
    return req

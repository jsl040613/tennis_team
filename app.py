from flask import Flask, render_template, request, redirect, session, url_for
from models.post_model import Post
from models.user_model import User
import os
from werkzeug.utils import secure_filename
from functools import wraps
from bson import ObjectId
from db import db  # Import db module

app = Flask(__name__)
app.secret_key = "your_secret_key"

# File upload configuration
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    """Check if the uploaded file is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def login_required(f):
    """Decorator to check if the user is logged in"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        if User.login(username, password):
            session['user'] = username
            session['following'] = User.get_following(username)  # Ensure following field exists
            return redirect(url_for('dashboard'))
        else:
            return "Invalid username or password", 401
    return render_template('login.html')

@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        User.register(username, password)
        return redirect('/login')
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/court_booking', methods=['GET', 'POST'])
def court_booking():
    if request.method == 'POST':
        court_name = request.form['court_name']
        date = request.form['date']
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        username = session.get('user')  # Get the currently logged-in user

        booking = {
            'username': username,
            'court_name': court_name,
            'date': date,
            'start_time': start_time,
            'end_time': end_time
        }
        db.bookings.insert_one(booking)  # Insert into MongoDB

        return redirect(url_for('user_profile', username=username))  # Redirect to user profile

    return render_template('court_booking.html')

@app.route('/create_post', methods=["GET", "POST"])
@login_required
def create_post():
    if request.method == "POST":
        content = request.form.get('content')
        good_posts = request.form.get('good_posts')
        quantity = request.form.get('quantity')
        price = request.form.get('price')
        username = session.get('user')

        image_dynamic_path, image_good_post_path = None, None
        
        for img_type in ['image_dynamic', 'image_good_post']:
            file = request.files.get(img_type)
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                if img_type == 'image_dynamic':
                    image_dynamic_path = filename
                else:
                    image_good_post_path = filename
        

        image_path = image_dynamic_path or image_good_post_path
        Post.create_post(username, content, image_path, good_posts, quantity, price)

        return redirect('/feed') if content else redirect(f'/user/{username}')

    return render_template('create_post.html')

@app.route('/feed')
def feed():        
    posts = list(db.posts.find({'good_posts': None}))
    for post in posts:
        post['_id'] = str(post['_id'])
    return render_template('feed.html', posts=posts)

@app.route('/like/<post_id>', methods=['POST'])
@login_required
def like(post_id):
    Post.add_like(ObjectId(post_id), session.get('user'))
    return redirect(url_for('feed'))

@app.route('/comment/<post_id>', methods=['POST'])
@login_required
def comment(post_id):
    Post.add_comment(ObjectId(post_id), session.get('user'), request.form.get('comment'))
    return redirect(url_for('feed'))

@app.route('/comments/<post_id>')
def comments(post_id):
    post = Post.find_by_id(ObjectId(post_id))
    post['_id'] = str(post['_id'])
    return render_template('comment_list.html', post=post)

@app.route('/user/<username>')
def user_profile(username):
    user_posts = list(db.posts.find({'username': username, 'content': {'$ne': None}, 'good_posts': None}))
    good_finds_posts = list(db.posts.find({'username': username, 'good_posts': {'$ne': None}, 'content': None}))
    court_reservations = list(db.bookings.find({'username': username}))  # Correct collection used

    for post_list in [user_posts, good_finds_posts]:
        for post in post_list:
            post['_id'] = str(post['_id'])

    return render_template(
        'user_profile.html',
        username=username,
        posts=user_posts,
        good_finds_posts=good_finds_posts,
        court_reservations=court_reservations
    )

@app.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    try:
        current_user = session.get('user')
        if not current_user:
            return "Unauthorized", 401
        
        User.follow(current_user, username)
        session['following'] = User.get_following(current_user)  # Update session['following']
        
    except KeyError as e:
        return f"Error: Missing key {e}", 400
    return redirect(url_for('feed'))

@app.route('/logout')
@login_required
def logout():
    return redirect(url_for('login'))  # 跳转到登录页面


@app.route('/following')
@login_required
def following():
    following_list = session.get('following', [])  # Ensure session doesn't throw KeyError
    return render_template('following.html', following=following_list)

@app.route('/followers')
@login_required
def followers():
    current_user = session.get('user')
    followers_list = User.get_followers(current_user)
    return render_template('followers.html', followers=followers_list)


if __name__ == "__main__":
    app.run(debug=True)

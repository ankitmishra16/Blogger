import os
import secrets
from PIL import Image
from flask import render_template, url_for, flash, redirect, request, abort, send_from_directory
from flaskblog import app, db, bcrypt, mail
from flaskblog.forms import (RegistrationForm, LoginForm, UpdateAccountForm, AddCommentForm,
                             PostForm, RequestResetForm, ResetPasswordForm)
from flaskblog.models import User, Post, Comment, PostLike, Choice
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message
from flask_ckeditor import CKEditor, CKEditorField, upload_fail, upload_success
from sqlalchemy import func


@app.route("/")
def welcome():
    return render_template('welcome.html')


@app.route("/home")
def home():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.filter_by(published=True).order_by(Post.date_posted.desc()).paginate(page=page, per_page=6)
    query1 = (db.session.query(PostLike.post_id, PostLike.title, func.count(PostLike.post_id))
              .group_by(PostLike.post_id, PostLike.title)
              .having(func.count(PostLike.post_id) > 0)
              .order_by(func.count(PostLike.post_id).desc())
              .limit(5))

    result = dict(zip([0, 1, 2, 3, 4], query1))

    return render_template('home2.html', posts=posts, result=result)


@app.route("/about")
def about():
    return render_template('about.html', title='About')


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    i = Image.open(form_picture)
    i.save(picture_path)

    return picture_fn


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.aboutme = form.aboutme.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.aboutme.data = current_user.aboutme
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account',
                           image_file=image_file, form=form)


@app.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, author=current_user,
                    user_tag=form.user_tag.data.name, theme=form.theme.data)
        if form.submit.data:
            print("save")
            post.published = True
            db.session.add(post)
            db.session.commit()
            flash('Your post has been Published!', 'success')
            return redirect(url_for('home'))
        elif form.save.data:
            db.session.add(post)
            db.session.commit()
            flash('Your post has been Saved!', 'success')
            return redirect(url_for('home'))

    return render_template('create_post.html', title='New Post',
                           form=form, legend='New Post', new=True)


@app.route("/post/<int:post_id>")
def post(post_id):
    post = Post.query.get_or_404(post_id)
    print(post.user_id)
    print(post.published)
    print(current_user)
    print(post.theme)
    if not post.published:
        if not post.author == current_user:
            abort(403)
    comments = Comment.query.filter_by(post_id=post_id)
    form = AddCommentForm()
    if post.theme == 2:
        return render_template('post2.html', title=post.title, post=post, form=form, comments=comments)
    elif post.theme == 3:
        return render_template('post3.html', title=post.title, post=post, form=form, comments=comments)
    else:
        return render_template('post.html', title=post.title, post=post, form=form, comments=comments)




@app.route("/post/<int:post_id>/publish", methods=['GET', 'POST'])
@login_required
def publish_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    post.published = True
    db.session.commit()
    flash('Your post has been Published!', 'success')
    return redirect(url_for('post', post_id=post.id))




@app.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        post.user_tag = form.user_tag.data.name
        theme = request.form['theme']
        post.theme = int(theme)
        print('printing theme in post')
        print(post.theme)
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
        form.user_tag.data = post.user_tag
        form.theme.data = post.theme
        print(form.theme.data)
    return render_template('create_post.html', title='Update Post',
                           form=form, legend='Update Post', new=False)


@app.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('home'))


@app.route("/user/<string:username>")
def user_posts(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user) \
        .order_by(Post.date_posted.desc()) \
        .paginate(page=page, per_page=5)
    return render_template('user_posts.html', posts=posts, user=user)


@app.route("/user/<string:username>/all")
def all_user_posts(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user) \
        .order_by(Post.date_posted.desc()) \
        .paginate(page=page, per_page=5)
    return render_template('all_user_posts.html', posts=posts, user=user)


@app.route("/user/<string:username>/published")
def published_user_posts(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user, published=True) \
        .order_by(Post.date_posted.desc()) \
        .paginate(page=page, per_page=5)
    return render_template('published_user_posts.html', posts=posts, user=user)


@app.route("/user/<string:username>/unpublished")
@login_required
def unpublished_user_posts(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user, published=False) \
        .order_by(Post.date_posted.desc()) \
        .paginate(page=page, per_page=5)
    return render_template('unpublished_user_posts.html', posts=posts, user=user)


def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request',
                  sender='noreply@demo.com',
                  recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}

If you did not make this request then simply ignore this email and no changes will be made.
'''
    mail.send(msg)


@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title='Reset Password', form=form)


@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)


@app.route("/post/<int:post_id>", methods=['GET', 'POST'])
def comment_post(post_id):
    post = Post.query.get_or_404(post_id)
    form = AddCommentForm()
    if form.validate_on_submit():
        db.create_all()
        if current_user.is_authenticated:
            comment = Comment(body=form.body.data, post_id=post_id, username=current_user.username,
                              comment_user_id=current_user.id)
        else:
            comment = Comment(body=form.body.data, post_id=post_id, username='Anonymous')
        db.session.add(comment)
        db.session.commit()
        flash('Your comment has been added to the post', 'success')
        return redirect(url_for('post', post_id=post_id))
    return render_template('post.html', title=post.title, form=form, post=post)


@app.route('/files/<filename>')
def uploaded_files(filename):
    path = app.config['UPLOADED_PATH']
    return send_from_directory(path, filename)


@app.route('/upload', methods=['POST'])
def upload():
    f = request.files.get('upload')
    extension = f.filename.split('.')[1].lower()
    if extension not in ['jpg', 'gif', 'png', 'jpeg']:
        return upload_fail(message='Image only!')
    f.save(os.path.join(app.config['UPLOADED_PATH'], f.filename))
    url = url_for('uploaded_files', filename=f.filename)
    return upload_success(url=url)


@app.route("/post/like/<int:post_id>/<action>")
@login_required
def like_action(post_id, action):
    post = Post.query.filter_by(id=post_id).first_or_404()
    if action == 'like':
        current_user.like_post(post)
        db.session.commit()
    if action == 'unlike':
        current_user.unlike_post(post)
        db.session.commit()
    return redirect(request.referrer)


@app.route("/search", methods=['Post'])
def search():
    value = request.form.get('tag')
    posts = Post.query.filter_by(user_tag=value).all()
    return render_template('search_result.html', value=value, posts=posts)

@app.errorhandler(404)
def error_404(error):
    return render_template('404.html'),404

@app.errorhandler(403)
def error_403(error):
    return render_template('403.html'),403

@app.route("/user/<string:username>/comments")
def comments_posts(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = (db.session.query(Post.id,Post.title,Comment.id,Comment.body)
            .join(Comment)
            .filter(Post.id==Comment.post_id))

    rows = (db.session.query(Post.id,Post.title,Comment.id,Comment.body)
            .join(Comment)
            .filter(Post.id==Comment.post_id)).count()

    result = dict(zip([i for i in range(rows)],posts))
    return render_template('comments_posts.html',result=result)

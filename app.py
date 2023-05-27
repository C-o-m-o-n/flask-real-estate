#import all the necessary packages
from flask import Flask, render_template, url_for, request, redirect, flash, session, jsonify
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import random
import os
from time import  localtime, strftime
from sqlalchemy import MetaData
from flask_migrate import Migrate
from flask_socketio import SocketIO, send, emit, join_room, leave_room

#initialise Flask
app = Flask(__name__)
#old sqlite database
app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///database.db'
#new mysql database
# mysql://root:T0vJWROg3RdqmKjgCbW8@containers-us-west-121.railway.app:6705/railway
# app.config['SQLALCHEMY_DATABASE_URI']='mysql+pymysql://root:iHUPZcoYYUQ96En6chw2@containers-us-west-55.railway.app:6549/railway'

app.config['SECRET_KEY']='sqlite:///database'

#for user session
app.permanent_session_lifetime = timedelta(minutes=10)
#for socketio(chats)
socketio = SocketIO(app)
ROOMS = ["Lounge", "News", "Gamming", "Code"]

#initialise SQLAlchemy with Flask
convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}
metadata = MetaData(naming_convention=convention)
db = SQLAlchemy(app, metadata=metadata)
migrate = Migrate(app,db,render_as_batch=True)



login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
login_manager.init_app(app)
#default Column id

id_list =[]
for i in range(1000000):
  id_list.append(i)
  uid = random.choice(id_list)
  

#define the BlogPost table
class BlogPost(db.Model,UserMixin):
  id = db.Column(db.Integer, primary_key=True)
  date_posted = db.Column(db.DateTime)
  content = db.Column(db.String(256))
  post_img_1 = db.Column(db.String(100))
  post_img_2 = db.Column(db.String(100))
  post_img_3 = db.Column(db.String(100))
  price = db.Column(db.String(256))
  bed_no = db.Column(db.String(256))
  bath_no = db.Column(db.String(256))
  county = db.Column(db.String(256))
  purpose = db.Column(db.String(256))
  street = db.Column(db.String(256))
  area = db.Column(db.String(256))
  date_posted = db.Column(db.DateTime)
  #foreign key to link to other tables
  poster_id = db.Column(db.Integer, db.ForeignKey('users.id'))
  comments = db.relationship('Comments', backref='blog_post')
  likes = db.relationship('Likes', backref='post')

#define the Users table

class Users(db.Model,UserMixin):
  id = db.Column(db.Integer, primary_key=True)
  first_name = db.Column(db.String(250))
  surname = db.Column(db.String(250))
  email = db.Column(db.String(250))
  phone = db.Column(db.String(250), default='')
  address1 = db.Column(db.String(250), default='')
  address2 = db.Column(db.String(250), default='')
  county = db.Column(db.String(250), default='')
  area = db.Column(db.String(250), default='')
  password = db.Column(db.String(256))
  profile_pic = db.Column(db.String(250), default='user.png')
  pic_file_path = db.Column(db.String(256))
  date_joined = db.Column(db.DateTime)
  #user can have many ppsts
  blog_post = db.relationship('BlogPost', backref='poster')
  likes = db.relationship('Likes', backref='liker')
  comments = db.relationship('Comments', backref='comenter')
  
# define comments table
class Comments(db.Model, UserMixin):
  id = db.Column(db.Integer, primary_key=True)
  username = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='cascade'))#represents the user
  content = db.Column(db.String(100))
  date_posted = db.Column(db.DateTime)
  post_id = db.Column(db.Integer, db.ForeignKey('blog_post.id', ondelete='cascade'))


#define the Likes table
class Likes(db.Model,UserMixin):
  id = db.Column(db.Integer, primary_key=True)
  username = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='cascade'))#represents the user
  date_posted = db.Column(db.DateTime)
  #user can have many ppsts
  post_id = db.Column(db.Integer, db.ForeignKey('blog_post.id', ondelete='cascade'))


#main app code starts here****************((*))
  
with app.app_context(): 
  #put all the code inside the app context
  #the homepage
  @app.route('/')
  def index():
	  posts = []
	  all_posts = BlogPost.query.all()
	  for i in all_posts:
		  posts.append(i)
		  posts_length  = len(all_posts)
		  last_four = posts_length-1
		  posts = posts[-last_four:]
	  print("posts price: ", [post.county for post in posts])
	  print(posts_length)
	  return render_template("index.html", posts=posts, current_user=current_user )
  
  #the properties page
  @app.route('/propertise')
  def properties():
    posts = BlogPost.query.all()
    return render_template("properties.html", posts=posts, current_user=current_user )
    
  #like page
  @app.route('/like/<int:post_id>', methods=['POST'])
  @login_required
  def like(post_id):
    post = BlogPost.query.filter_by(id=post_id).first()
    
    like = Likes.query.filter_by(username=current_user.id, post_id=post_id).first()
    if not post:
      return jsonify({'error': 'post does not exist.'}, 400)
      flash('the post does not exist', 'error')
    elif like:
      db.create_all()
      db.session.delete(like)
      db.session.commit()
    else:
      like= Likes(username=current_user.id, post_id=post_id)
      db.create_all()
      db.session.add(like)
      db.session.commit()
    return jsonify({'likes' : len(post.likes), 'liked' : current_user.id in map(lambda x: x.username, post.likes)})

 
  #the post page
  @app.route('/post/<int:post_id>', methods=['GET','POST'])
  @login_required
  def post(post_id):
    post = BlogPost.query.filter_by(id=post_id).one()
    #comment_id = Comments.query.filter_by(id=post_id).one()
    date_posted = post.date_posted.strftime('%B, %d, %Y')
    #post_id = BlogPost.query.get(post_id)
    if request.method == 'POST':
      if request.form['content']:
        comment = Comments(username=current_user.id, content=request.form['content'], post_id=post_id)
        db.create_all()
        db.session.add(comment)
        db.session.commit()
        flash("Your comment has been added to the post", "success")
        return redirect(url_for("post", post_id=post_id))
      else:
        flash('no Comments was entered', 'error')
        
    comments = Comments.query.filter_by(post_id=post_id)
    likes = Likes.query.filter_by(post_id=post_id)
    return render_template("property-single.html", post=post, date_posted=date_posted, post_id=post_id, comments=comments, likes=likes)
  
  #the page for adding posts 8 the frontend  
  @app.route('/add')
  @login_required
  def add():
    return render_template("add.html")
    
  #handles the posts
  def save_post_img(form_pic): 
    random_pic_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_pic.filename)
    post_pic_file_name = random_pic_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/assets/post_img', post_pic_file_name)
    form_pic.save(picture_path)
    
    return post_pic_file_name
    
  @app.route('/addpost', methods=['GET', 'POST'])
  def add_property():
      if request.method == "POST":
          content_img = request.files['post_img_1']
          content = request.form['content']
          county = request.form['county']
          street = request.form['street']
          price = request.form['price']
          bath_no = request.form['bath_no']
          bed_no = request.form['bed_no']
          area = request.form["area"]
          purpose = request.form["purpose"]
          poster = current_user.id
          if content_img:
              post_img_1 = save_post_img(request.files['post_img_1'])
              post_img_2 = save_post_img(request.files['post_img_2'])
              post_img_3 = save_post_img(request.files['post_img_3'])
              post = BlogPost(post_img_1=post_img_1, post_img_2=post_img_2, post_img_3=post_img_3, purpose=purpose, poster_id=poster, content=content, area=area, date_posted=datetime.now(), price=price, street=street, county=county, bath_no=bath_no, bed_no=bed_no )
              db.create_all()
              db.session.add(post)
              db.session.commit()
              flash("the property has been added successfully", 'successs')
              return redirect(url_for('index'))
          elif not content_img:
              flash("please provide an image of the property", "error")
              return redirect(url_for('index'))
      return render_template('add_property.html')
  #posts code ends*************((*))
  
  #user accounts starts************((*))
  @login_manager.user_loader
  def load_user(id):
    return Users.query.get(int(id))

  @app.route('/login', methods=['POST', 'GET'])
  def login():
    if current_user.is_authenticated:
      flash("you are already loged in", 'info')
      return redirect(url_for('index'))
    if request.method == 'POST':
      session.permanent = True
      email = request.form['email']
      password = request.form['password']
      surname = request.form['surname']
      user = Users.query.filter_by(email=email).first()
      if user:
        password_is_same =check_password_hash(user.password, password)
        if password_is_same:
          flash("loged in successfully", 'success')
          session["user"]=surname
          login_user(user, remember=True)
          next_page = request.args.get('next')
          return redirect(url_for(next_page)) if next_page else redirect(url_for('index'))
        else:
          flash("The surname or password is incorrect", 'error')
      else:
        flash("email does not exist", "error")
    return render_template('login.html')
    
  #save the image to the file system
  def save_pic(form_pic): 
    random_pic_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_pic.filename)
    pic_file_name = random_pic_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/assets/profile_img', pic_file_name)
    form_pic.save(picture_path)
    
    return pic_file_name
    
  #user profile
  @app.route('/user', methods=['POST', 'GET'])
  @login_required
  def user():
    profile_pic = url_for('static', filename='assets/profile_img/'+ current_user.profile_pic)
    #updating the profile details
    if request.method == "POST":
      if request.files['profile_pic']:
        picture_file = save_pic(request.files['profile_pic'])
        current_user.profile_pic = picture_file
        
      #get username and email from the form
      first_name = request.form['first_name']
      surname = request.form['surname']
      phone = request.form['phone']
      address1 = request.form['address1']
      address2 = request.form['address2']
      postcode = request.form['postcode']
      county = request.form['county']
      area = request.form['area']
      


      current_user.surname = surname
      current_user.first_name = first_name
      current_user.phone = phone
      current_user.address1 = address1
      current_user.address2 = address2
      current_user.postcode = postcode
      current_user.county = county
      current_user.area = area
      db.session.commit()
      flash("your profile has been updated successfully", "success")
      return redirect(url_for('index'))
        
    if 'user' in session:
      user_session = session["user"]
      user = Users.query.filter_by(surname=current_user.surname).first()
      return render_template("user.html",title="profile", user_session=user_session, current_user=current_user, profile_pic=profile_pic)
    else:
      return redirect(url_for('login'))
      
  @app.route('/signup', methods=['POST', 'GET'])
  def signup():
    if current_user.is_authenticated:
      flash("you are already signed up", 'error')
      return redirect(url_for('index'))
    if request.method == 'POST':
      first_name = request.form['first_name']
      surname = request.form['surname']
      email = request.form['email']
      password1 = request.form['password1']
      password2 = request.form['password2']
      
      email_exists = Users.query.filter_by(email=email).first()
      surname_exists = Users.query.filter_by(surname=surname).first()
      if email_exists:
        flash('email i already in use', 'error')
      elif surname_exists:
        flash('username i already in use', 'error')
      elif password1 != password2:
          flash('passwords do not match', 'error')
      elif len(surname) <= 2:
        flash('username is too short', 'error')
      elif len(password1) <= 6:
        flash('password is too short', 'error')
      elif len(email) <= 4:
        flash('email is invalid', 'error')
      else:
        new_user = Users(first_name=first_name, surname=surname, email=email, password=generate_password_hash(password1, method='sha256'))
        db.create_all()
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user, remember=True)
        flash('user created successfully','success')
        return redirect(url_for('index'))
    return render_template('signup.html')
  
  @app.route('/upgrade')
  def upgrade():
    return render_template('upgrade.htnl')
  #the chat page
  #events handles
  @socketio.on('message')
  def message(data):
    print(f'\n{data}\n')
    send({'msg':data['msg'], 'username': data['username'], 'profileImg': data['profileImg'], 'time_stamp': strftime('%b-%d-%Y-- %H:%M-%p', localtime())}, room=data['room'])#sends the message to event called message
  # joining rooms 
  @socketio.on('join')
  def join(data):
    join_room(data['room'])
    send({'msg': data['username'] + '  has joined the '+ data['room'] + ' ' + ' room.'}, room=data['room'])
  
  #leaving rooms
  @socketio.on('leave')
  def leave(data):
    leave_room(data['room'])
    send({'msg': data['username'] + '  has left the '+ data['room']+ '  room.'}, room=data['room'])
      
  @app.route('/chat')
  def chat():
    chat_sender = Users.query.filter_by(username=current_user.username).first()
    return render_template("chat.html", username=current_user.username, rooms=ROOMS, chat_sender=chat_sender )
  #end of chat page


    #logout
  @app.route('/logout')
  @login_required
  def logout():
    logout_user()
    session.pop("user", None)
    return redirect(url_for('index'))
  
  #run the Flask app
  if __name__ == "__main__":
    
    socketio.run(app, debug=True)

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, current_user, login_required
from werkzeug.utils import secure_filename
import os
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate 
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired
from flask_wtf.file import FileField, FileAllowed 


app = Flask(__name__)

app.config['SECRET_KEY'] = 'your_secret'  # Replace with a secure secret key
app.static_folder = 'static' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'  # You can use any database URL here
app.config['profile_pics'] = os.path.join(app.root_path, 'static', 'profile_pics')

db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager(app)  # Create a LoginManager instance
login_manager.login_view = 'login'  # Set the login view


@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)


class User(UserMixin, db.Model):
    
    id = db.Column(db.Integer, primary_key=True)
    user_type = db.Column(db.String(20), nullable=False, default='labourer')
    location = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False) 
    password = db.Column(db.String(100), nullable=False)
    business_profile = db.relationship('BusinessProfile', backref='user', uselist=False)
    profile_image = db.relationship('UserProfileImage', backref='user', uselist=False)

class UserProfileImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(100), nullable=False)
    


class BusinessProfile(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    id = db.Column(db.Integer, 
    primary_key=True)
    business_name = db.Column(db.String(100), nullable=False)
    business_type = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    suburb = db.Column(db.String(100), nullable=False)
    street = db.Column(db.String(100), nullable=False)
    number = db.Column(db.String(10), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)

class NewBusinessProfileForm(FlaskForm):
    business_name = StringField('Business Name', validators=[DataRequired()])
    business_type = StringField('Business Type', validators=[DataRequired()])
    city = StringField('City', validators=[DataRequired()])
    suburb = StringField('Suburb', validators=[DataRequired()])
    street = StringField('Street', validators=[DataRequired()])
    number = StringField('Number', validators=[DataRequired()])
    phone_number = StringField('Phone Number', validators=[DataRequired()])
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    submit = SubmitField('Save Changes')

class UploadProfileImageForm(FlaskForm):
    profile_image = FileField('Upload Profile Image', validators=[FileAllowed(['jpg', 'png', 'jpeg'])])
    submit = SubmitField('Upload')



@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))  # Load a user by ID


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user_type = request.form.get('userType')
        location = request.form.get('location')
        email = request.form.get('email')
        password = request.form.get('password')
        hashed_password = generate_password_hash(password, method='sha256')
        
        new_user = User(user_type=user_type, location=location, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        return redirect(url_for('login'))
        
    return render_template('register.html') 


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            if user.user_type == 'labourer':
                return redirect(url_for('labourer_dashboard'))
            else:
                return redirect(url_for('business_dashboard'))

    return render_template('login.html')  # Create a corresponding HTML template

@app.route('/labourer/dashboard')
@login_required
def labourer_dashboard():
    return render_template('labourer_home.html', current_user=current_user)

@app.route('/business/dashboard')
@login_required
def business_dashboard():
    return render_template('business_home.html', current_user=current_user)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        file = request.files['profile_image']
        if file and file.filename:
            filename = secure_filename(file.filename)
            profile_image_path = os.path.join(app.config['profile_pics'], filename)
            file.save(profile_image_path)

            # Update user's profile image in the database
            if not current_user.profile_image:
                profile_image = UserProfileImage(filename=filename, user_id=current_user.id)
                db.session.add(profile_image)
                current_user.profile_image = profile_image
            else:
                current_user.profile_image.filename = filename
            db.session.commit()

    # Check if the user has a profile image, if not, assign the default image
    if not current_user.profile_image:
        default_image_filename = 'default_profile_pic.jpg'
        profile_image = UserProfileImage(filename=default_image_filename, user_id=current_user.id)
        db.session.add(profile_image)
        current_user.profile_image = profile_image
        db.session.commit()

    return render_template('business_profile.html')







@app.route('/profile/business')
@login_required
def business_profile():
    # Fetch the full profile information of the current business user from the database
    user = current_user

    # Assuming you have a user's business profile information
    business_profile = user.business_profile

    return render_template('business_profile.html', user=user, form=UploadProfileImageForm())



from flask import render_template, flash, redirect, url_for
from werkzeug.utils import secure_filename
import os


@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    user = User.query.get(current_user.id)
    form = NewBusinessProfileForm()

    if user.business_profile is None:
        user.business_profile = BusinessProfile()  # Create a new BusinessProfile object

    if form.validate_on_submit():
        # Manually populate business_profile attributes from form data
        user.business_profile.business_name = form.business_name.data
        user.business_profile.business_type = form.business_type.data
        user.business_profile.city = form.city.data
        user.business_profile.suburb = form.suburb.data
        user.business_profile.street = form.street.data
        user.business_profile.number = form.number.data
        user.business_profile.phone_number = form.phone_number.data
        user.business_profile.first_name = form.first_name.data
        user.business_profile.last_name = form.last_name.data

        db.session.commit()
        flash('Profile updated successfully', 'success')
        return redirect(url_for('business_profile'))

    # Pre-fill the form with existing business profile data
    form.process(obj=user.business_profile)

    return render_template('edit_profile_business.html', form=form)

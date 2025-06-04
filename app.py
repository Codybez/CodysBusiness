from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, current_user, login_required, logout_user
from werkzeug.utils import secure_filename
import os
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate 
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired
from flask_wtf.file import FileField, FileAllowed 
from forms import NewBusinessProfileForm
from forms import UploadProfileImageForm
from forms import EditLabourerProfileForm
from sqlalchemy import Column, Date
from datetime import datetime
from flask import jsonify
from sqlalchemy.sql import expression
from flask import abort
from flask_socketio import SocketIO, emit, join_room, leave_room
from sqlalchemy import and_
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.types import JSON
from flask import Flask
from flask_bcrypt import Bcrypt
from flask_mail import Mail 
from flask_mail import Message as emailmessage
from itsdangerous import URLSafeTimedSerializer
from flask import current_app
from threading import Thread
from dotenv import load_dotenv
from flask_session import Session
from flask_wtf.csrf import CSRFProtect
from datetime import datetime, timezone
import pytz
import stripe
from flask import send_from_directory

load_dotenv()

app = Flask(__name__)
csrf = CSRFProtect(app)





SECRET_KEY = os.environ.get('SECRET_KEY', 'this')

app.config['WTF_CSRF_SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-secret-key')

app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")


bcrypt = Bcrypt(app)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Define the path to your production database
prod_db_path = '/home/codybeznec/CodysBusiness/instance/new_database.db'

# Define the path to your local database (replace with your local path)
local_db_path = 'sqlite:///new_database.db'

# Check if the production database exists
if os.path.exists(prod_db_path):
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{prod_db_path}'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = local_db_path



  # You can use any database URL here
app.config['profile_pics'] = os.path.join(app.root_path, 'static', 'profile_pics')


serializer = URLSafeTimedSerializer(SECRET_KEY)

socketio = SocketIO(app)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager(app)  # Create a LoginManager instance
login_manager.login_view = 'login'  # Set the login view
login_manager.init_app(app)


# Email Configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))  # Default to 587 if missing
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS') == 'True'
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

mail = Mail(app)


@app.route('/', methods=['GET', 'POST']) 
@csrf.exempt
def index():
    if request.method == 'POST':
        # Pull the form fields
        name = request.form.get('name')
        email = request.form.get('email')
        message_body = request.form.get('Message')  # <-- careful: 'Message' must match name attribute in form
        
        # Create the email message
        msg = emailmessage(
            subject=f"New Public Contact Form Submission: {name}",
            sender=email,
            recipients=[os.getenv('MAIL_USERNAME')],  # Sending to your saved email
            body=f"From: {name}\nEmail: {email}\n\nMessage:\n{message_body}"
        )
        
        try:
            mail.send(msg)
            flash('Your message has been sent successfully!', 'success')
        except Exception as e:
            print(f"Error sending message: {e}")
            flash('An error occurred while sending your message.', 'danger')

        return redirect(url_for('index'))  # Just reload homepage after submit

    # GET method: normal page load
    return render_template('index.html')

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    soft_deleted = db.Column(db.Boolean, default=False)  # New column for soft delete
    email_verified = db.Column(db.Boolean, default=False)  # Column to track if email is verified
    verification_token = db.Column(db.String(500), nullable=True)  # New column for verification token
    user_type = db.Column(db.String(20), nullable=False, default='labourer')
    location = db.Column(db.String(500), nullable=False)
    email = db.Column(db.String(500), unique=True, nullable=False)
    password = db.Column(db.String(500), nullable=False)
    first_name = db.Column(db.String(50), nullable=True)  # Initially nullable
    last_name = db.Column(db.String(50), nullable=True)   # Initially nullable
    jobs_completed = db.Column(db.Integer, default=0)
    date_created = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)  # New field
    is_admin = db.Column(db.Boolean, default=False)  # Admin status
    business_profile = db.relationship('BusinessProfile', backref='user', uselist=False)
    profile_image = db.relationship('UserProfileImage', backref='user', uselist=False)
    labourer_profile = db.relationship('LabourerProfile', backref='user', uselist=False)
    company_details = db.relationship('CompanyDetails', uselist=False)
    social_links = db.relationship('SocialLinks', backref='user', uselist=False, lazy=True)
    jobs = db.relationship('Job', backref='user', lazy=True)  # Keep this

class UserProfileImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(100), nullable=False)
    


class BusinessProfile(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    id = db.Column(db.Integer, 
    primary_key=True)
    jobs = db.relationship('Job', backref='business_profile', lazy=True)

class LabourerProfile(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    id = db.Column(db.Integer, 
    primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    date_of_birth = Column(Date)
    phone_number = db.Column(db.String(20), nullable=False)
    user_blurb = db.Column(db.String(250), nullable=False)
    job_categories = db.Column(db.String(500), nullable=True)
    job_locations = db.Column(db.String(500), nullable=True) 
    id_image = db.Column(db.String(120), nullable=True)
    verification_ready = Column(db.Boolean, default=False)
    insurance_image = db.Column(db.String(120),nullable=True)
    id_verified = db.Column(db.Boolean, default=False)
    insurance_verified = db.Column(db.Boolean, default=False) 
    company_details_locked = db.Column(db.Boolean, default=False) 

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_name = db.Column(db.String(100), nullable=False)
    job_category = db.Column(db.String(100), nullable=False)
    contact_number = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(100), nullable=True)
    city = db.Column(db.String(100), nullable=False)
    suburb = db.Column(db.String(100), nullable=False)
    tasks = db.Column(db.String(250), nullable=False)
    image_paths = db.Column(db.String(255))
    additional_details = db.Column(db.String(250))
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='open')  # 'open', 'applied', 'closed', etc.
    applicants = db.relationship('JobApplication', backref='job', lazy=True)
    accepted_user_id = db.Column(db.Integer, nullable=True)
    business_profile_id = db.Column(db.Integer, db.ForeignKey('business_profile.id'), nullable=False)
    payment_required = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Foreign key to User
    # Remove the duplicate `user` relationship from the Job model

class JobApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    is_visible = db.Column(db.Boolean, default=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'accepted', 'rejected', etc.
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='user_profile_image', lazy=True)



class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime(timezone=True))
    is_read = db.Column(db.Boolean, default=False, nullable=True)
    room = db.Column(db.String(50), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey
    ('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    job_application_id = db.Column(db.Integer, db.ForeignKey('job_application.id'), nullable=True)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    read = db.Column(db.Boolean, default=False)
    notification_type = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime(timezone=True))
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=True)  
    job = db.relationship('Job', backref='notifications', lazy=True)
    user2_id = db.Column(db.Integer, nullable=True)  # Add user2_id here
    job_application_id = db.Column(db.Integer, db.ForeignKey('job_application.id'), nullable=True)
    job_application = db.relationship('JobApplication', backref='notifications', lazy=True)

    user = db.relationship('User', backref=db.backref('notifications', lazy=True))

    def __repr__(self):
        return f'<Notification {self.id} for User {self.user_id}>'

class CompanyDetails(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    business_type = db.Column(db.String(100), nullable=False)
    nzbn = db.Column(db.String(100))
    director_first_name = db.Column(db.String(50), nullable=False)
    director_last_name = db.Column(db.String(50), nullable=False)
    physical_address = db.Column(db.String(100), nullable=False)
    unit_no = db.Column(db.String(10))
    trading_name = db.Column(db.String(100), nullable=False)
    established = db.Column(db.String(100), nullable=True)

    

class SocialLinks(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    facebook = db.Column(db.String(255))
    instagram = db.Column(db.String(255))
    website = db.Column(db.String(255))
    google= db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Post(db.Model):
    __tablename__ = 'posts'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    job_location_name = db.Column(db.String(100), nullable=False)  # Just storing the name
    city_suburb = db.Column(db.String(100), nullable=False)
    job_category_name = db.Column(db.String(100), nullable=False)  # Just storing the name
    post_images = db.Column(db.String, nullable=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    saved_by_users = Column(MutableList.as_mutable(JSON), default=[])
    user = db.relationship('User', backref=db.backref('posts', lazy=True))

    def __repr__(self):
        return f"<Post {self.title}>"
    
    def add_saved_user(self, user_id):
        # Add user_id to the list if it's not already present
        if user_id not in self.saved_by_users:
            self.saved_by_users.append(user_id)
    
    def remove_saved_user(self, user_id):
        # Remove user_id from the list if present
        if user_id in self.saved_by_users:
            self.saved_by_users.remove(user_id)


class Chat(db.Model):
    __tablename__ = 'chats'

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)  # Links to the Post
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Sender of the message
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Receiver of the message
    content = db.Column(db.Text, nullable=False)  # The chat message content
    timestamp = db.Column(db.DateTime(timezone=True))  # When the message was sent
    room = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)  # Notification field for unread/read status

    # Relationships
    post = db.relationship('Post', backref=db.backref('chats', lazy=True))
    sender = db.relationship('User', foreign_keys=[sender_id], backref=db.backref('sent_chats', lazy=True))
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref=db.backref('received_chats', lazy=True))

    def __repr__(self):
        return f"<Chat sender={self.sender_id}, receiver={self.receiver_id}, post_id={self.post_id}>"


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=True)  # ForeignKey for Job
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # ForeignKey for User
    professionalism = db.Column(db.Integer, nullable=True)
    quality = db.Column(db.Integer, nullable=True)
    cost = db.Column(db.Integer, nullable=True)
    communication = db.Column(db.Integer, nullable=True)
    comments = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=True)

    # Relationships
    job = db.relationship('Job', backref='reviews', lazy=True)
    user = db.relationship('User', backref='reviews', lazy=True)

    def __repr__(self):
        return f"<Review {self.id} for Job {self.job_id}>"

class GearPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    equipment_type = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(50), nullable=False)
    city_suburb = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    is_rental = db.Column(db.Boolean, default=True)  
    price = db.Column(db.Float, nullable=True)
    price_per_day = db.Column(db.Float, nullable=True)
    price_per_week = db.Column(db.Float, nullable=True) 
    price_per_half_day = db.Column(db.Float, nullable=True) 
    rental_duration = db.Column(db.String(20), nullable=True)  
    image_url = db.Column(db.String(200), nullable=True) 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    pickup_only = db.Column(db.Boolean, default=True)
    delivery_available = db.Column(db.Boolean, default=False)
    bond_required = db.Column(db.Boolean, default=False)
    bond_amount = db.Column(db.Float, nullable=True)



@app.route('/landing_page')
def landing_page():
    return render_template('landing_page.html')



@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))  # Load a user by ID



from itsdangerous import BadSignature, SignatureExpired

@app.route('/verify_email/<token>')
def verify_email(token):
    try:
        # Deserialize the token and get the email from it, with a 1-hour expiration time
        email = serializer.loads(token, salt='email-verify-salt', max_age=3600)
    except SignatureExpired:
        flash('The verification link has expired.', 'danger')
        return redirect(url_for('login'))
    except BadSignature:
        flash('Invalid or tampered verification link.', 'danger')
        return redirect(url_for('login'))

    # Find the user by the email
    user = User.query.filter_by(email=email).first()

    if user:
        # Mark the user's email as verified
        user.email_verified = True
        user.verification_token = None  # Remove the token after successful verification
        db.session.commit()

        flash('Your email has been verified! You can now log in.', 'success')
        return redirect(url_for('login'))
    else:
        flash('User not found.', 'danger')
        return redirect(url_for('login'))


def generate_verification_token(email):
    serializer = URLSafeTimedSerializer(SECRET_KEY)
    return serializer.dumps(email, salt='email-verify-salt')




@app.route('/register', methods=['GET', 'POST'])
@csrf.exempt
def register():
    if request.method == 'POST':
        user_type = request.form.get('userType')
        location = request.form.get('location')
        email = request.form.get('email')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')

        # Check if the email already exists in the database
        user = User.query.filter_by(email=email).first()

        if user:
            if user.soft_deleted:
                flash('This email is associated with a deactivated account. Please contact support to reactivate your account.', 'error')
            else:
                flash('An active account already exists with this email. Please log in.', 'error')
            return redirect(url_for('login'))  # Redirect to login page if email exists

        # If the email doesn't exist, create a new user
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')


        serializer = URLSafeTimedSerializer(SECRET_KEY)

        # Generate a token using itsdangerous with an expiration time of 1 hour (3600 seconds)
        token = serializer.dumps(email, salt='email-verify-salt')

        # Create the new user
        new_user = User(
            email=email,
            password=hashed_password,
            location=location,
            user_type=user_type,
            first_name=first_name,
            last_name=last_name,
            verification_token=token  # Store the token in the User model
        )
        db.session.add(new_user)
        db.session.commit()

        # If the user is a business, create a BusinessProfile with the user_id automatically
        if user_type == 'Business':
            business_profile = BusinessProfile(
                user_id=new_user.id  # Link the new business profile to the user
            )
            db.session.add(business_profile)
            db.session.commit()

        # Generate the verification link with the token
        verification_link = url_for('verify_email', token=token, _external=True)

        # Prepare the context for the email
        email_context = {
            'user': new_user,
            'verification_link': verification_link
        }

        # Send the email asynchronously
        send_async_email(
            to=email,
            subject='Please verify your email',
            template_name='email/email_verification.html',
            context=email_context
        )


        flash('Registration successful! A verification email has been sent to your inbox.', 'info')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
@csrf.exempt
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if user:
            # Check if the password is correct and if the account is not soft deleted
            if bcrypt.check_password_hash(user.password, password):


                if user.soft_deleted:
                    flash('Your account has been deactivated. Please contact support.', 'error')
                    return redirect(url_for('login'))
                
                if not user.email_verified:
                    flash('Please verify your email address before logging in.', 'error')
                    return redirect(url_for('login'))

                # If the account is not soft deleted and the email is verified, log the user in
                login_user(user)

                # Redirect based on user type
                if user.is_admin:
                    return redirect(url_for('admin_dashboard'))  # Admins go to admin dashboard
                elif user.user_type == 'Business':
                    return redirect(url_for('business_created_jobs'))
                else:
                    return redirect(url_for('find_a_job'))
            else:
                flash('Invalid password. Please try again.', 'error')
        else:
            flash('No account found with this email address.', 'error')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()

   
    return redirect(url_for('index'))  # Redirect to the login page after logout


def notify_matching_tradesmen_async(category, location, job_name, tasks, job_id):
    # Fetch users with matching preferences from LabourerProfile
    matching_users = User.query.join(LabourerProfile).filter(
        LabourerProfile.job_categories.ilike(f"%{category}%"),
        LabourerProfile.job_locations.ilike(f"%{location}%")
    ).all()

    # Get the employer's name
    employer_name = current_user.first_name  # Assuming `current_user` is the employer who posted the job

    # Send emails asynchronously to the matching users
    for user in matching_users:
        send_job_notification_email_async(user, job_name, tasks, job_id, employer_name, category, location)

def send_job_notification_email_async(user, job_name, tasks, job_id, employer_name, job_category, location):
    subject = f"New Job Opportunity: {job_name} in {location}"
    template_name = 'email/job_notification_email.html'
    context = {
        'first_name': user.first_name,
        'job_name': job_name,
        'tasks': tasks,
        'job_id': job_id,
        'employer_name': employer_name,  # Include employer's name here
        'job_category': job_category,  # Include job category here
        'location': location,  # Include location here
        'message_link': url_for('login', job_id=job_id, _external=True)
    }
    send_async_email(user.email, subject, template_name, context)

@app.route('/submit_job', methods=['POST'])
@csrf.exempt
def submit_job():
    if current_user.is_authenticated:
        if current_user.user_type == 'Business' and current_user.business_profile:
            business_profile_id = current_user.business_profile.id

            # Handle file upload
            image_paths = []
            if 'photo-upload' in request.files:
                photo_uploads = request.files.getlist('photo-upload')
                for photo_upload in photo_uploads:
                    if photo_upload.filename != '':
                        filename = secure_filename(photo_upload.filename)
                        file_path = os.path.join('/home/codybeznec/CodysBusiness/static/job_images', filename)
                        photo_upload.save(file_path)
                        image_paths.append(filename)

            # Extract form fields
            job_name = request.form['job_name']
            job_category = request.form['job-category']
            location = request.form.get('location')  # Get the location field
            city = request.form['city']
            suburb = request.form['suburb']

            tasks = request.form['tasks']
            additional_details = request.form.get('additional-details')
            contact_number = request.form.get('contact_number')  # Get the contact number

            # Validate location
            valid_locations = [
                "Northland", "Auckland", "Waikato", "Bay of Plenty", "Gisborne", "Hawke's Bay", 
                "Taranaki", "Manawatū-Whanganui", "Wellington", "Tasman", "Nelson", "Marlborough", 
                "West Coast", "Canterbury", "Otago", "Southland"
            ]
            if location not in valid_locations:
                flash('Invalid location selected.', 'error')
                return redirect(url_for('create_job'))

            # Create a new job instance
            job = Job(
                job_name=job_name,
                job_category=job_category,
                location=location,
                city=city,
                suburb=suburb,
                contact_number=contact_number,
                tasks=tasks,
                additional_details=additional_details,
                business_profile_id=business_profile_id,
                user_id=current_user.id,
                image_paths=','.join(image_paths) if image_paths else None
            )

            # Save the job to the database
            db.session.add(job)
            db.session.commit()

            # Notify tradesmen matching the job category and location
            notify_matching_tradesmen_async(job_category, location, job_name, tasks, job.id)

            flash('Job submitted successfully!', 'success')
            return redirect(url_for('business_created_jobs'))
        
        else:
            flash('You must have a business profile to submit a job.', 'error')
            return redirect(url_for('create_business_profile'))
    else:
        flash('You must be logged in to submit a job.', 'error')
        return redirect(url_for('login'))

@app.route('/job/<int:job_id>')
def display_job(job_id):
    # Retrieve the job from the database with the related business profile
    job = (
        Job.query
        .join(BusinessProfile, Job.business_profile_id == BusinessProfile.id)
        .filter(Job.id == job_id)
        .first()
    )

    if job:
        return render_template('display_job.html', job=job)
    else:
        return "Job not found", 404


@app.route('/labourer/dashboard')
@login_required
def labourer_dashboard():
    return render_template('labourer_home.html',is_dashboard_page=True, current_user=current_user)

@app.route('/business/dashboard')
@login_required
def business_dashboard():
    return render_template('business_home.html',is_dashboard_page=True, current_user=current_user)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
@csrf.exempt
def profile():
    if request.method == 'POST':
        file = request.files['profile_image']
        if file and file.filename:
            filename = secure_filename(file.filename)
            profile_image_path = os.path.join(app.config['profile_pics'], filename)
            file.save(profile_image_path)

            # Check if the user has a profile image, if not, create a new one
            if current_user.profile_image is not None:
                current_user.profile_image.filename = filename
            else:
                new_profile_image = UserProfileImage(user_id=current_user.id, filename=filename)
                db.session.add(new_profile_image)

            db.session.commit()

    # Check if the user has a profile image, if not, assign the default image
    if not current_user.profile_image:
        default_image_filename = 'orange.png'
        current_user.profile_image = UserProfileImage(user_id=current_user.id, filename=default_image_filename)
        db.session.add(current_user.profile_image)
        db.session.commit()

    return render_template('business_profile.html')

@app.route('/profile/labourer/image', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def labourer_image():
    if request.method == 'POST':
        file = request.files['profile_image']
        if file and file.filename:
            filename = secure_filename(file.filename)
            profile_image_path = os.path.join(app.config['profile_pics'], filename)
            file.save(profile_image_path)

            # Update user's profile image in the database
            if current_user.profile_image is not None:
                current_user.profile_image.filename = filename
            else:
                new_profile_image = UserProfileImage(user_id=current_user.id, filename=filename)
                db.session.add(new_profile_image)

            db.session.commit()

    # Check if the user has a profile image, if not, assign the default image
    if current_user.profile_image is None:
        default_image_filename = 'orange.png'
        current_user.profile_image = UserProfileImage(user_id=current_user.id, filename=default_image_filename)
        db.session.add(current_user.profile_image)
        db.session.commit()

    return render_template('labourer_profile.html',is_dashboard_page=True,user=current_user)

@app.route('/profile/business')
@login_required
@csrf.exempt
def business_profile():
    # Fetch the full profile information of the current business user from the database
    user = current_user

    # Assuming you have a user's business profile information
    business_profile = user.business_profile

    return render_template('business_profile.html', user=user, is_dashboard_page=True, business_profile=business_profile, form=UploadProfileImageForm())

# ...
from sqlalchemy.orm import joinedload



@app.route('/profile/labourer')
@login_required
def labourer_profile():
    # Fetch the full profile information of the current labourer user from the database
    user = (
        User.query
        .options(joinedload(User.company_details))  # Eagerly load company_details
        .filter_by(id=current_user.id)
        .first()
    )

    # Assuming you have a user's labourer profile information
    labourer_profile = user.labourer_profile

    # Fetch company details if available
    company_details = user.company_details

    # Check if the labourer profile exists
    if not labourer_profile:
        return render_template(
            'labourer_profile.html',
            user=user,
            labourer_profile=None,  # Pass None to indicate the profile needs to be created
            company_details=company_details,
            verification_ready=False,
            id_verified=False
        )

    return render_template(
        'labourer_profile.html',
        user=user,
        labourer_profile=labourer_profile,
        company_details=company_details,
        verification_ready=labourer_profile.verification_ready,
        id_verified=labourer_profile.id_verified, is_dashboard_page=True
    )



@app.route('/profile/edit', methods=['GET', 'POST'])
@csrf.exempt
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


@app.route('/profile/labourer/edit', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def edit_labourer_profile():
    user = User.query.get(current_user.id)
    form = EditLabourerProfileForm()

    if form.validate_on_submit():
        # Ensure that the first_name and last_name are populated before committing
        if user.labourer_profile is None:
            user.labourer_profile = LabourerProfile()  # Create a new LabourerProfile object if it doesn't exist

        # Manually populate labourer_profile attributes from form data
        user.labourer_profile.phone_number = form.phone_number.data
        user.labourer_profile.user_blurb = form.user_blurb.data
        user.labourer_profile.date_of_birth = form.date_of_birth.data

        # Set the first_name and last_name on both the User and LabourerProfile models
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.labourer_profile.first_name = form.first_name.data
        user.labourer_profile.last_name = form.last_name.data

        # Commit changes to the database
        db.session.commit()
        flash('User info updated successfully', 'success')
        return redirect(url_for('labourer_profile'))

    # Pre-fill the form with existing data from both User and LabourerProfile models
    form.first_name.data = user.first_name
    form.last_name.data = user.last_name
    if user.labourer_profile:
        form.phone_number.data = user.labourer_profile.phone_number
        form.user_blurb.data = user.labourer_profile.user_blurb
        form.date_of_birth.data = user.labourer_profile.date_of_birth

    return render_template('edit_profile_labourer.html', form=form)


from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from datetime import datetime

@app.route('/find_a_job')
@login_required
def find_a_job():
    # Check if the current user is a labourer and if their profile exists
    if not current_user.labourer_profile:
        flash("Please complete your profile.")
        return redirect(url_for('labourer_profile'))  # Redirect to profile completion page

    # Check if the profile is verified
    if not current_user.labourer_profile.id_verified:
        flash("This section will be available once your profile is verified.")
        return redirect(url_for('labourer_profile'))  # Redirect to profile completion page

    my_categories = current_user.labourer_profile.job_categories.split(', ') if current_user.labourer_profile.job_categories else []
    my_locations = current_user.labourer_profile.job_locations.split(', ') if current_user.labourer_profile.job_locations else []

    job_data = Job.query.join(User).filter(User.soft_deleted == False).all()

    # Ensure image_list is a list of paths
    for job in job_data:
        if job.image_paths:
            job.image_list = job.image_paths.split(',')
        else:
            job.image_list = []

    return render_template('find_a_job.html', job_data=job_data, my_categories=my_categories, my_locations=my_locations, is_dashboard_page=True)

@app.route('/create_job', methods=['GET'])
def create_job():
    # This will render the create job form
    return render_template('create_a_job.html', user=current_user, is_dashboard_page=True)



from flask import flash

# ... (previous imports) ...

@app.route('/apply_for_job/<int:job_id>')
@csrf.exempt
@login_required
def apply_for_job(job_id):
    job = Job.query.get_or_404(job_id)

    # Check if the user has already applied for this job
    application = JobApplication.query.filter_by(user_id=current_user.id, job_id=job.id).first()

    if application:
        # If application exists, update its status to 'paid'
        application.status = 'paid'
        db.session.commit()
        flash("Your application has been marked as paid!", "success")
    else:
        # Create a new job application with status 'paid'
        application = JobApplication(user_id=current_user.id, job_id=job.id, status='paid')
        db.session.add(application)
        db.session.commit()
        flash("Payment Succesful! Contact details are now available.", "success")

                # Notify the job poster
        create_job_application_notification(
            receiver_id=job.user_id,  # Assuming job.user_id is the poster's ID
            job_id=job.id,
            trading_name=f"{current_user.company_details.trading_name}",
            applicant_name=f"{current_user.first_name}"
        )

                # Prepare email context
        email_context = {
            "job_poster_name": job.user.first_name,  # Assuming `job.user` is the job poster
            "job_title": job.job_name,
            "applicant_name": current_user.first_name,
            "trading_name": current_user.company_details.trading_name,                 "message_link": f"{request.url_root}login"  # Generate message link
        }

        # Send email notification
        send_async_email(
            to=job.user.email,  # Job poster's email
            subject=f"New Application for '{job.job_name}'",
            template_name="email/job_application_notification.html",  # Path to your HTML email template
            context=email_context
        )


    # Optionally, redirect the user to the job detail page or another page
    return redirect(url_for('applied_jobs', job_id=job.id))

@app.route('/applied_jobs')
@login_required
def applied_jobs():
    # Assuming you have a relationship between User and JobApplication
    applied_jobs = (
        Job.query
        .join(Job.applicants)
        .filter(and_(JobApplication.user_id == current_user.id, JobApplication.status == 'paid'))
        .all()
    )

    # Ensure 'image_list' contains the correct list of images for each job
    for job in applied_jobs:
        job.image_list = job.image_paths.split(',') if job.image_paths else []

    # Pass the current user as 'applicant' to the template
    return render_template('applied_jobs.html', applied_jobs=applied_jobs, applicant=current_user, is_dashboard_page=True)

@app.route('/business_created_jobs')
@login_required
def business_created_jobs():
    # Retrieve the business profile of the current user
    business_profile = current_user.business_profile

    if business_profile:
        # Retrieve only open status jobs created by the current business user
        created_jobs = Job.query.filter_by(business_profile_id=business_profile.id, status='open').all()

        # Ensure 'image_list' contains the correct list of images for each job
        for job in created_jobs:
            job.image_list = job.image_paths.split(',') if job.image_paths else []

        return render_template('business_open_jobs.html', created_jobs=created_jobs, is_dashboard_page=True)

    flash("Business profile not found.", "error")
    return redirect(url_for('business_dashboard'))



@app.route('/business_display_jobs/<int:job_id>')
@login_required
def business_display_jobs(job_id):
    job = Job.query.get_or_404(job_id)

    return render_template('business_display_jobs.html', job=job)

@app.route('/display_jobs/<int:job_id>')
@login_required
def display_jobs(job_id):
    job = Job.query.get_or_404(job_id)

    return render_template('display_job.html', job=job)

from flask_socketio import SocketIO, emit, join_room

socketio = SocketIO(app)


@app.route('/view_applicants/<int:job_id>', methods=['GET'])
def view_applicants(job_id):
    # Fetch the job applications for the given job_id
    job_applications = JobApplication.query.filter_by(job_id=job_id).all()

    # Check if job exists
    job = Job.query.get_or_404(job_id)

    # Include user details for each application
    for application in job_applications:
        application.user = User.query.get(application.user_id)

    return render_template(
        'viewapplicants.html',
        job=job,
        job_applications=job_applications
    )

@app.route('/process_applications/<int:job_id>/<int:user_id>', methods=['POST'])
@csrf.exempt
def process_applications(job_id, user_id):
    # Update the status of all applications for the job
    job_applications = JobApplication.query.filter_by(job_id=job_id).all()

    # Initialize accepted_user_id to None
    accepted_user_id = None

    for application in job_applications:
        if application.user_id == user_id:
            application.status = 'accepted'
            accepted_user_id = user_id  # Store the accepted user ID
        else:
            application.status = 'rejected'

    # Update the job's accepted_user_id and status
    job = Job.query.get(job_id)
    job.accepted_user_id = accepted_user_id
    job.status = 'booked'

    db.session.commit()

    flash('Applications processed successfully', 'success')
    return redirect(url_for('business_active_jobs', job_id=job_id, user_id=user_id))


@app.route('/confirm_user/<int:job_id>/<int:user_id>', methods=['GET'])
@csrf.exempt
@login_required
def confirm_user(job_id, user_id):
    # Fetch details about the accepted user and job
    user_details = get_user_details(user_id)
    job_details = get_job_details(job_id)
    selected_user = get_user_details
     
    return render_template('confirm_user.html', user_details=user_details, job_details=job_details, selected_user=selected_user)

def get_job_details(job_id):
    # Fetch job details from the database
    job = Job.query.filter_by(id=job_id).first()
    if not job:
        raise ValueError("Job not found")
    return job


@app.route('/chooseuser/<int:job_id>/<int:user_id>', methods=['GET'])
@login_required
def choose_user(job_id, user_id):
    # Fetch the job and user information
    job = Job.query.get(job_id)
    user = User.query.get(user_id)
    
    return render_template('confirm_user.html', job_details={'job': job}, selected_user=user)
# Assuming get_user_details is defined in your Flask application


def get_user_details(user_id):
    user = User.query.get(user_id)
    labourer_profile = LabourerProfile.query.filter_by(user_id=user_id).first()
    profile_image = UserProfileImage.query.filter_by(user_id=user_id).first()
    company_details = CompanyDetails.query.filter_by(user_id=user_id).first()
    
    return {
        'user': user,
        'labourer_profile': labourer_profile,
        'profile_image': profile_image,
         'company_details': company_details
         
    }



@app.route('/business_active_jobs')
@login_required
def business_active_jobs():
    # Retrieve the business profile of the current user
    business_profile = current_user.business_profile

    if business_profile:
        # Retrieve only 'closed' status jobs created by the current business user
        active_jobs = Job.query.filter_by(business_profile_id=business_profile.id, status='closed').all()

        # Ensure 'image_list' contains the correct list of images for each job
        for job in active_jobs:
            job.image_list = job.image_paths.split(',') if job.image_paths else []

        return render_template('business_active_jobs.html', active_jobs=active_jobs, get_user_details=get_user_details, is_dashboard_page=True)

    flash("Business profile not found.", "error")
    return redirect(url_for('business_dashboard'))



def time_ago(date):
    now = datetime.utcnow()
    delta = now - date
    if delta.days == 1:
        return '1 day ago'
    elif delta.days > 1:
        return f'{delta.days} days ago'
    elif delta.seconds >= 3600:
        hours = delta.seconds // 3600
        return f'{hours} hours ago'
    elif delta.seconds >= 60:
        minutes = delta.seconds // 60
        return f'{minutes} minutes ago'
    else:
        return 'just now'

app.jinja_env.filters['time_ago'] = time_ago


@app.route('/search_jobs')
def search_jobs():
    location = request.args.get('location')
    job_category = request.args.get('job-category')
    sort_by = request.args.get('sort-by', 'date')  # Default to sorting by date if not specified

    # Modify the database query to order by date_created in descending order
    query = Job.query.order_by(Job.date_created.desc())

    if location:
        query = query.filter(Job.location == location)

    if job_category:
        query = query.filter(Job.job_category == job_category)

    # Add sorting based on the selected option
    if sort_by == 'date':
        query = query.order_by(Job.date)
    elif sort_by == 'job-category':
        query = query.order_by(Job.job_category)
    # Add more sorting options as needed

    job_data = query.all()

    return render_template('your_template.html', job_data=job_data)

@app.route('/active_jobs')
@csrf.exempt
@login_required
def active_jobs():
    # Retrieve jobs where the current user has been accepted
    active_jobs = (
        Job.query
        .join(Job.applicants)
        .filter(
            and_(
                JobApplication.user_id == current_user.id,
                JobApplication.status == 'accepted'
            )
        )
        .options(joinedload(Job.user))  # Eager load the job poster's details
        .all()
    )
        # Ensure 'image_list' contains the correct list of images for each job
    for job in active_jobs:
        job.image_list = job.image_paths.split(',') if job.image_paths else []

    return render_template('active_jobs.html', active_jobs=active_jobs, applicant=current_user, is_dashboard_page=True)

@app.route('/remove_application/<int:job_id>')
@csrf.exempt
@login_required
def remove_application(job_id):
    # Find the job and application
    job = Job.query.get(job_id)
    if job:
        application = JobApplication.query.filter_by(user_id=current_user.id, job_id=job_id).first()
        if application:
            # Set application status to 'removed' instead of toggling visibility
            application.status = 'removed'
            db.session.commit()

    # Redirect back to the applied_jobs page
    return redirect(url_for('applied_jobs'))


@app.route('/delete_job/<int:job_id>', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def delete_job(job_id):
    job = Job.query.get(job_id)

    if job:
        # Check if the current user is the owner of the job
        if current_user.id == job.business_profile.user_id:
            # Delete job applications related to the job
            JobApplication.query.filter_by(job_id=job.id).delete()

            # Delete the job and commit changes
            db.session.delete(job)
            db.session.commit()

            flash('Job and associated applications deleted successfully', 'success')
        else:
            flash('You are not authorized to delete this job', 'error')

    # Redirect to the page where the job was listed (e.g., business_dashboard)
    return redirect(url_for('business_dashboard'))



@app.route('/edit_tradesman_profile', methods=['GET', 'POST'])
@csrf.exempt
def edit_tradesman_profile():
    if request.method == 'POST':
        # Similar to the previous route, handle the form submission
        business_type = request.form.get('businessType')
        nzbn = request.form.get('nzbn')
        director_first_name = request.form.get('directorFirstName')
        director_last_name = request.form.get('directorLastName')
        physical_address = request.form.get('physicalAddress')
        unit_no = request.form.get('unitNo')
        trading_name = request.form.get('tradingName')
        established = request.form.get('established')
        


        user = current_user

        # Check if the user has associated company_details
        if user.company_details is None:
            # Create a new CompanyDetails instance
            company_details = CompanyDetails(
                business_type=business_type,
                nzbn=nzbn,
                director_first_name=director_first_name,
                director_last_name=director_last_name,
                physical_address=physical_address,
                unit_no=unit_no,
                trading_name=trading_name,
                established=established
            )
            user.company_details = company_details
        else:
            # Update the existing CompanyDetails instance
            user.company_details.business_type = business_type
            user.company_details.nzbn = nzbn
            user.company_details.director_first_name = director_first_name
            user.company_details.director_last_name = director_last_name
            user.company_details.physical_address = physical_address
            user.company_details.unit_no = unit_no
            user.company_details.trading_name = trading_name
            user.company_details.established = established

        # Commit the changes to the database
        db.session.commit()

        flash("Company details updated succesfully")

        return redirect(url_for('labourer_profile'))

    # Render the tradesman profile page for editing
    return render_template('tradesman_profile.html')


@app.route('/review/<int:job_id>', methods=['GET', 'POST'])
@csrf.exempt
def tradesman_review(job_id):
    # Fetch the job details based on job_id
    job = Job.query.get(job_id)
    
    if not job:
        # If the job does not exist, return a 404 error
        abort(404)
    
    # Fetch the tradesman/user associated with this job (assuming accepted_user_id points to the user)
    selected_user = User.query.get(job.accepted_user_id)

    if not selected_user:
        # If no user is found for this job, return a 404 error
        abort(404)

    # Check if the user has already submitted a review for this job
    existing_review = Review.query.filter_by(user_id=selected_user.id, job_id=job_id).first()

    if request.method == 'POST':
        # Process the submitted review form data
        professionalism = int(request.form['professionalism'])
        quality = int(request.form['quality'])
        cost = int(request.form['cost'])
        communication = int(request.form['communication'])
        comments = request.form['comments']

        if existing_review:
            # If a review already exists, update it
            existing_review.professionalism = professionalism
            existing_review.quality = quality
            existing_review.cost = cost
            existing_review.communication = communication
            existing_review.comments = comments
            db.session.commit()
            flash('Review updated successfully!', 'success')
        else:
            # If no review exists, create a new one
            review = Review(
                job_id=job_id,
                user_id=selected_user.id,
                professionalism=professionalism,
                quality=quality,
                cost=cost,
                communication=communication,
                comments=comments
            )
            db.session.add(review)
            db.session.commit()
            flash('Review submitted successfully!', 'success')

        # Redirect back to the 'business_active_jobs' page after review submission
        return redirect(url_for('business_active_jobs'))

    # Pass the job object and any existing review to the template
    return render_template('labourer_review.html', job=job, selected_user=selected_user, existing_review=existing_review)

@app.route('/edit_social_links', methods=['GET', 'POST'])
@csrf.exempt
def edit_social_links():
    if request.method == 'POST':
        facebook = request.form.get('facebook')
        instagram = request.form.get('instagram')
        website = request.form.get('website')
        google = request.form.get('google')

        user = current_user

        # Check if the user has associated social_links
        if user.social_links is None:
            # Create a new SocialLinks instance
            social_links = SocialLinks(
                facebook=facebook,
                instagram=instagram,
                website=website,
                google=google,
            )
            user.social_links = social_links  # Associate the new SocialLinks with the user
        else:
            # Update the existing SocialLinks instance
            user.social_links.facebook = facebook
            user.social_links.instagram = instagram
            user.social_links.website = website
            user.social_links.google = google

        # Commit the changes to the database
        db.session.commit()

        return redirect(url_for('labourer_profile'))  # Redirect to profile page to view changes

    return render_template('edit_social_links.html')

@app.route('/tradesman_profile/<int:user_id>')
@csrf.exempt
def view_tradesman_profile(user_id):
    # Query the database for the user
    user = User.query.get_or_404(user_id)  # Get the user by ID
    reviews = Review.query.filter_by(user_id=user_id).all()  # Fetch reviews for the user
    overall_rating = calculate_overall_rating(user)
    
    if not user:
        # If the user does not exist, return a 404 error
        abort(404)

   
    # Render the profile page with the user's data
    return render_template(
        'view_tradesman_profile.html',
        user=user,reviews=reviews,overall_rating=overall_rating
    )

@app.route('/notifications/unread')
@login_required
@csrf.exempt
def get_unread_notifications():
    notifications = Notification.query.filter_by(
        user_id=current_user.id,
        read=False
    ).all()
    
    
    return jsonify({
        "notifications": [{"id": n.id, "message": n.message, "timestamp": n.timestamp, "notification_type": n.notification_type, 
                           "job_id": n.job_id, "job_application_user_id": n.job_application_user_id, "read": n.read} for n in notifications]
    })

@app.route('/notifications/<int:notification_id>', methods=['POST'])
@login_required
@csrf.exempt
def mark_notification_read(notification_id):
    notification = Notification.query.get(notification_id)
    if notification and notification.user_id == current_user.id:
        notification.read = True
        db.session.commit()
        return jsonify({"status": "Notification marked as read!"}), 200
    
    return jsonify({"error": "Notification not found or not yours"}), 404

@app.route('/notifications/delete/<int:notification_id>', methods=['POST'])
@login_required
@csrf.exempt
def delete_notification(notification_id):
    notification = Notification.query.get(notification_id)
    if notification and notification.user_id == current_user.id:
        db.session.delete(notification)
        db.session.commit()
        return jsonify({"status": "Notification deleted!"}), 200
    
    return jsonify({"error": "Notification not found or not yours"}), 404



def create_message_notification(receiver_id, message_content, job_application_id=None, job_id=None):
    try:
        if job_application_id:
            job_application = JobApplication.query.get(job_application_id)
            job_id = job_application.job.id if job_application else None

            notification = Notification(
                user_id=receiver_id,
                message=message_content,
                read=False,
                notification_type='message',
                timestamp=datetime.utcnow(),
                job_application_id=job_application_id,
                job_id=job_id
            )
        elif job_id:
            notification = Notification(
                user_id=receiver_id,
                message=message_content,
                read=False,
                notification_type='message',
                timestamp=datetime.utcnow(),
                job_id=job_id
            )
        else:
            return None  # Handle if no job_id or job_application_id is provided
        
        db.session.add(notification)
        db.session.commit()
        print(f"Notification created: {notification}")  # Log to check notification creation
    except Exception as e:
        print(f"Error creating notification: {e}")
        db.session.rollback()  # Rollback in case of error
    return notification


@app.route('/notifications')
@csrf.exempt
@login_required
def notifications():
    # Fetch the notifications for the current user
    notifications = Notification.query.filter_by(user_id=current_user.id).all()

    # Convert timestamps to NZST (New Zealand Standard Time)
    nz_tz = pytz.timezone('Pacific/Auckland')
    for notification in notifications:
        notification.timestamp = notification.timestamp.astimezone(nz_tz)  # Convert to NZST

    # Render the notifications page template with the notifications data
    return render_template('notifications.html', notifications=notifications, is_dashboard_page=True)


@app.context_processor
def inject_unread_notifications_count():
    # Check if the user is authenticated before querying
    if current_user.is_authenticated:
        unread_count = Notification.query.filter_by(user_id=current_user.id, read=False).count()
    else:
        unread_count = 0  # If the user is not logged in, there are no unread notifications
    return dict(unread_notifications_count=unread_count)


def create_job_application_notification(receiver_id, job_id, applicant_name, trading_name):
    """
    Create a notification for a new job application.
    """
    try:
        # Validate input
        if not receiver_id or not job_id:
            print(f"Invalid input: receiver_id={receiver_id}, job_id={job_id}, applicant_name={applicant_name}")
            return False

        # Create notification
        notification = Notification(
            user_id=receiver_id,
            message=f"{applicant_name} from {trading_name} has applied for your job.",
            read=False,
            notification_type='job_application',
            timestamp=datetime.utcnow(),
            job_id=job_id
        )
        db.session.add(notification)
        db.session.commit()
        print(f"Job application notification created: {notification}")
        return notification
    except Exception as e:
        # Handle errors
        print(f"Error creating job application notification: {e}")
        db.session.rollback()
        return False
 
@app.route('/business_completed_jobs')
@csrf.exempt
@login_required
def business_completed_jobs():
    # Retrieve the business profile of the current user
    business_profile = current_user.business_profile

    if business_profile:
        # Retrieve only 'closed' status jobs created by the current business user
        completed_jobs = Job.query.filter_by(business_profile_id=business_profile.id, status='closed').all()

        return render_template('business_active_jobs.html', completed_jobs=completed_jobs, get_user_details=get_user_details)

    flash("Business profile not found.", "error")
    return redirect(url_for('business_dashboard'))

@app.route('/contact', methods=['GET', 'POST'])
@csrf.exempt
def contact():
    if request.method == 'POST':
        # Get form data
        name = request.form['name']
        email = request.form['email']
        message_body = request.form['message']

        # Prepare the email
        msg = emailmessage(
            subject=f"New Contact Form Message from {name}",
            sender=email,  # So you know who sent it
            recipients=[os.getenv('MAIL_USERNAME')],  # send it to your own email
            body=f"From: {name}\nEmail: {email}\n\nMessage:\n{message_body}"
        )

        try:
            mail.send(msg)
            flash('Your message has been sent successfully!', 'success')
        except Exception as e:
            print(f"Error sending email: {e}")
            flash('An error occurred while sending your message.', 'danger')

        return redirect(url_for('contact'))

    return render_template('contact_us.html')

@app.route('/select_job_categories_and_locations', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def select_job_categories_and_locations():
    # Predefined categories and locations
    categories = [
        'General Labouring', 'Construction', 'Landscaping', 'Cleaning', 'Painting', 
        'Plumbing', 'Electrical', 'Carpentry', 'Roofing', 'HVAC', 'Moving', 'Gardening', 'Handyman','Window Glazing','Tiling', 'Flooring', 'Concreting', 'Whiteware Repair', 'Other'
    ]
    locations = [
        'Northland', 'Auckland', 'Waikato', 'Bay of Plenty', 'Gisborne', 'Hawke\'s Bay', 
        'Taranaki', 'Manawatū-Whanganui', 'Wellington', 'Tasman', 'Nelson', 'Marlborough', 
        'West Coast', 'Canterbury', 'Otago', 'Southland'
    ]

    # Ensure the labourer profile exists
    if current_user.labourer_profile:
        selected_categories = current_user.labourer_profile.job_categories.split(', ') if current_user.labourer_profile.job_categories else []
        selected_locations = current_user.labourer_profile.job_locations.split(', ') if current_user.labourer_profile.job_locations else []
    else:
        selected_categories = []
        selected_locations = []

    if request.method == 'POST':
        # Get selected categories and locations from the form submission
        selected_categories = request.form.get('categories', '').split(',')
        selected_locations = request.form.get('locations', '').split(',')

        # Update the current user's profile with the selected categories and locations
        if current_user.labourer_profile:
            current_user.labourer_profile.job_categories = ', '.join(selected_categories)
            current_user.labourer_profile.job_locations = ', '.join(selected_locations)
            db.session.commit()

        # Redirect to the profile page or any other page after saving the selections
        return redirect(url_for('labourer_profile'))

    return render_template('select_job_categories_and_locations.html', 
                           categories=categories, 
                           locations=locations,
                           selected_categories=selected_categories,
                           selected_locations=selected_locations)

@app.route('/close_job/<int:job_id>', methods=['GET', 'POST'])
@csrf.exempt
def close_job(job_id):
    job = Job.query.get(job_id)

    if request.method == 'POST':
        job_filled = request.form.get('job_filled')
        
        if job_filled == 'yes':
            # Get the selected applicant's name and company to match
            completion_choice = request.form.get('completion_choice')
            
            selected_applicant = next(
                (app for app in job.applicants if f"{app.user.first_name} from {app.user.company_details.trading_name}" == completion_choice),
                None
            )

            if selected_applicant:
                # Mark the selected applicant as accepted
                selected_applicant.status = 'accepted'  # Set the status to 'accepted'
                
                # Set the accepted user on the job
                job.accepted_user_id = selected_applicant.user.id  # Mark the applicant as accepted in Job

        else:
            # If the job wasn't filled, reset accepted_user_id
            job.accepted_user_id = None

        # Set the job status to closed
        job.status = 'closed'

        
        # Check if there is an accepted user and send the notification
        if job.accepted_user_id:
            create_job_acceptance_notification(
                receiver_id=job.accepted_user_id,
                job_name=job.job_name,
                job_id=job.id,
                employer_name=current_user.first_name  # Use first name of the employer
            )

        db.session.commit()  # Save changes to the database

        flash("The job has been closed.", "success")
        return redirect(url_for('business_active_jobs'))  # Redirect to the completed jobs page

    return render_template('close_job.html', job=job)


def create_job_acceptance_notification(receiver_id, job_id, employer_name,job_name):
    """
    Create a notification for the accepted applicant when the job is closed.
    """
    try:
        if not receiver_id or not job_id or not employer_name:
            raise ValueError("Missing required parameters to create notification.")

        notification = Notification(
            user_id=receiver_id,
            message=f"Congratulations! You have been selected for the job '{job_name}' posted by {employer_name}.",
            read=False,
            notification_type="job_closed",  # Type is 'job_closed' for this specific notification
            timestamp=datetime.utcnow(),
            job_id=job_id
        )
        db.session.add(notification)
        db.session.commit()
        print("Job closure notification created successfully.")
        return notification
    except Exception as e:
        print(f"Error creating job closure notification: {e}")
        db.session.rollback()
        return None

@app.route('/find-tradies', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def find_tradies():
    # Ensure the user has a labourer profile
    if not current_user.labourer_profile:
        flash("Please complete your profile.")
        return redirect(url_for('labourer_profile'))

    # Ensure profile is verified
    if not current_user.labourer_profile.id_verified:
        flash("This section will be available after your profile is verified.", 'warning')
        return redirect(url_for('labourer_profile'))

    # Get the user's preferred categories and locations
    my_categories = current_user.labourer_profile.job_categories.split(', ') if current_user.labourer_profile.job_categories else []
    my_locations = current_user.labourer_profile.job_locations.split(', ') if current_user.labourer_profile.job_locations else []

    # Fetch all posts initially
    posts_query = Post.query

    # Get filters from request args (if provided)
    selected_category = request.args.get('category', 'all')
    selected_location = request.args.get('location', 'all')

    # Apply category filter
    if selected_category != 'all' and selected_category != 'my_categories':
        posts_query = posts_query.filter(Post.job_category_name == selected_category)
    elif selected_category == 'my_categories' and my_categories:
        posts_query = posts_query.filter(Post.job_category_name.in_(my_categories))

    # Apply location filter
    if selected_location != 'all' and selected_location != 'my_locations':
        posts_query = posts_query.filter(Post.job_location_name == selected_location)
    elif selected_location == 'my_locations' and my_locations:
        posts_query = posts_query.filter(Post.job_location_name.in_(my_locations))

    # Execute the query to get filtered posts
    active_posts = posts_query.all()

    # Prepare post_images for each post
    for post in active_posts:
        # Split post_images into a list (comma-separated string)
        post_images = post.post_images.split(', ') if post.post_images else []
        post.post_images_list = post_images  # Adding this list to the post object for use in the template

    return render_template(
        'find_tradies.html',
        active_posts=active_posts,
        my_categories=my_categories,
        my_locations=my_locations,
        selected_category=selected_category,
        selected_location=selected_location,
        is_dashboard_page=True
    )

import os
from werkzeug.utils import secure_filename

@app.route('/create_tradie_post', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def create_tradie_post():
    try:
        # Handle job posting
        if request.method == 'POST':
            # Fetch form data
            job_title = request.form.get('job_title')
            job_category_name = request.form.get('job_category')
            job_location_name = request.form.get('job_location')
            city_suburb = request.form.get('city_suburb')
            job_details = request.form.get('job_details')

            # Debugging: Log the inputs
            print(f"Job Title: {job_title}, Category: {job_category_name}, Location: {job_location_name}, Details: {job_details}")

            # Validate input
            if not job_title or not job_category_name or not job_location_name or not job_details:
                flash("All fields are required.", 'danger')
                return redirect(url_for('create_tradie_post'))

            # Handle image uploads
            post_images = []
            allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
            files = request.files.getlist('post_images')

            upload_folder = os.path.join(app.root_path,'static', 'tradies_post_images')
            os.makedirs(upload_folder, exist_ok=True)  # Ensure the folder exists

            for file in files:
                if file and '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(upload_folder, filename)

                    # Ensure unique filenames
                    counter = 1
                    while os.path.exists(file_path):
                        filename = f"{os.path.splitext(filename)[0]}_{counter}{os.path.splitext(filename)[1]}"
                        file_path = os.path.join(upload_folder, filename)
                        counter += 1

                    file.save(file_path)
                    post_images.append(filename)
                elif file.filename:  # If an invalid file was provided
                    flash(f"Invalid file format: {file.filename}. Only PNG, JPG, and GIF are allowed.", 'danger')
                    return redirect(url_for('create_tradie_post'))

            # Store image filenames as a comma-separated string
            post_images_str = ','.join(post_images) if post_images else None

            # Create the new post
            new_post = Post(
                title=job_title,
                description=job_details,
                job_location_name=job_location_name,
                city_suburb=city_suburb,
                job_category_name=job_category_name,
                user_id=current_user.id,
                post_images=post_images_str  # Save images here
            )

            # Add and commit the post to the database
            db.session.add(new_post)
            db.session.commit()

            # Debugging: Log post ID after commit
            print(f"New Post created with ID: {new_post.id}")

            # Flash success and redirect
            flash('Your job post has been created!', 'success')
            return redirect(url_for('tradies_my_posts', post_id=new_post.id))  

        # Render the form
        return render_template('create_tradie_post.html', is_dashboard_page=True)

    except Exception as e:
        # Debugging: Log the error
        print(f"Error in create_tradie_post: {e}")
        flash("An unexpected error occurred. Please try again later.", 'danger')
        return redirect(url_for('create_tradie_post'))

@app.route('/edit_tradie_post/<int:post_id>', methods=['GET', 'POST'])
@csrf.exempt
def edit_tradie_post(post_id):
    post = Post.query.get_or_404(post_id)

    # Convert existing images string to a list
    post_images = post.post_images.split(',') if post.post_images else []

    if request.method == 'POST':
        # Update post details
        post.title = request.form['job_title']
        post.job_category_name = request.form['job_category']
        post.job_location_name = request.form['job_location']
        post.city_suburb = request.form['city_suburb']
        post.description = request.form['job_details']

        # Handle image uploads
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
        files = request.files.getlist('post_images')

        print("FILES RECEIVED:", files)  # Debugging step

        upload_folder = os.path.join(app.root_path,'static', 'tradies_post_images')
        os.makedirs(upload_folder, exist_ok=True)  # Ensure the folder exists

        for file in files:
            if file and file.filename:  # Ensure the file is valid
                file_ext = file.filename.rsplit('.', 1)[1].lower()

                if file_ext in allowed_extensions:
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(upload_folder, filename)

                    # Ensure unique filenames
                    counter = 1
                    while os.path.exists(file_path):
                        filename = f"{os.path.splitext(file.filename)[0]}_{counter}{os.path.splitext(file.filename)[1]}"
                        file_path = os.path.join(upload_folder, filename)
                        counter += 1

                    file.save(file_path)
                    post_images.append(filename)  # Add new image to the list

                else:
                    flash(f"Invalid file format: {file.filename}. Only PNG, JPG, JPEG, and GIF are allowed.", 'danger')
                    return redirect(url_for('edit_tradie_post', post_id=post_id))

        # Store updated images as a comma-separated string
        post.post_images = ','.join(post_images) if post_images else None

        print("UPDATED IMAGES:", post.post_images)  # Debugging step

        db.session.commit()
        flash('Post updated successfully!', 'success')
        return redirect(url_for('tradies_my_posts'))  # Redirect after saving

    return render_template('edit_tradie_post.html', post=post, post_images=post_images)  


@app.route('/remove_image', methods=['POST'])
@csrf.exempt
def remove_image():
    data = request.get_json()
    image_filename = data.get('image_filename')
    post_id = data.get('post_id')  # Get post ID from request

    print("DEBUG: Received request to remove image")
    print(f"DEBUG: image_filename = {image_filename}")
    print(f"DEBUG: post_id = {post_id}")

    if not image_filename or not post_id:
        print("ERROR: Missing required data")
        return jsonify({"success": False, "message": "Missing required data"}), 400

    # Delete the image file from the server
    upload_folder = os.path.join(app.root_path,'static', 'tradies_post_images')
    file_path = os.path.join(upload_folder, image_filename)

    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"DEBUG: Successfully deleted {file_path}")
    else:
        print("ERROR: Image file not found on server")
        return jsonify({"success": False, "message": "Image file not found"}), 404

    # Update the database: remove the image from the post's images list
    post = Post.query.get(post_id)  
    if post:
        post_images = post.post_images.split(',') if post.post_images else []
        if image_filename in post_images:
            post_images.remove(image_filename)
            post.post_images = ','.join(post_images) if post_images else None
            db.session.commit()
            print("DEBUG: Updated database successfully")
        else:
            print("ERROR: Image filename not found in database")
            return jsonify({"success": False, "message": "Image not found in post data"}), 404
    else:
        print("ERROR: Post not found in database")
        return jsonify({"success": False, "message": "Post not found"}), 404

    return jsonify({"success": True})


@app.route('/save_post/<int:post_id>', methods=['GET', 'POST'])
@login_required
def save_post(post_id):
    post = Post.query.get(post_id)
    if post:
        user = current_user  # Assuming the user is logged in
        
        # Ensure saved_by_users is not None
        if post.saved_by_users is None:
            post.saved_by_users = []

        # Add user ID to the post's saved_by_users list if not already added
        if user.id not in post.saved_by_users:
            post.add_saved_user(user.id)  # Using the method we created earlier
            db.session.commit()
            flash('Post saved successfully!', 'success')
        else:
            flash('You have already saved this post!', 'info')
    else:
        flash('Post not found!', 'error')

    return redirect(url_for('tradies_saved_posts'))  # Redirect to the desired page after saving

@app.route('/remove_saved_post/<int:post_id>', methods=['POST' , 'GET'])
@login_required
def remove_saved_post(post_id):
    post = Post.query.get_or_404(post_id)
    if current_user.id in post.saved_by_users:
        post.remove_saved_user(current_user.id)
        db.session.commit()
        flash('Post removed from saved posts.', 'success')
    else:
        flash('Post not found in saved list.', 'error')
    
    return redirect(url_for('tradies_saved_posts'))

@app.route('/delete_post/<int:post_id>', methods=['POST'])
@csrf.exempt
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    # Ensure the current user is the owner of the post
    if post.user_id != current_user.id:
        abort(403)  # Unauthorized if not the owner

    # Remove the post from the saved_by_users list of all users who saved it
    for user_id in post.saved_by_users:
        user = User.query.get(user_id)
        if user:
            post.remove_saved_user(user.id)  # Remove the user from the saved posts list
            db.session.commit()

    # Delete the post
    db.session.delete(post)
    db.session.commit()

    flash('Post deleted successfully!', 'success')
    return redirect(url_for('tradies_my_posts'))  # Redirect to the user's posts page

@app.route('/tradies_saved_posts')
@csrf.exempt
@login_required  # Ensure the user is logged in
def tradies_saved_posts():
    # Get the current logged-in user
    user = current_user
    
    # Query all posts where the current user is in the saved_user_ids list
    saved_posts = Post.query.filter(Post.saved_by_users.contains([user.id])).all()

    return render_template('tradies_saved_posts.html', saved_posts=saved_posts, is_dashboard_page=True
    )



@app.route('/tradies_my_posts', methods=['GET'])
@login_required
def tradies_my_posts():
    # Fetch the current user's posts
    posts = Post.query.filter_by(user_id=current_user.id).all()

    return render_template('tradies_my_posts.html', posts=posts, is_dashboard_page=True)



@app.route('/get_messages/<int:job_application_id>', methods=['GET'])
def get_messages(job_application_id):
    messages = Message.query.filter_by(job_application_id=job_application_id).order_by(Message.timestamp).all()
    messages_data = [
        {
            "content": msg.content,
            "sender_id": msg.sender_id,
            "timestamp": msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }
        for msg in messages
    ]
    return jsonify(messages_data)

def send_email_async(app, to, subject, html_body):
    with app.app_context():
        msg = emailmessage(
            subject=subject,
            recipients=[to],
            html=html_body  # Set HTML body here
        )
        mail.send(msg)

def send_async_email(to, subject, template_name, context):
    """Send an email asynchronously using a rendered HTML template."""
    html_body = render_template(template_name, **context)
    thread = Thread(target=send_email_async, args=(current_app._get_current_object(), to, subject, html_body))
    thread.start()

@app.route('/chat/<int:job_id>/<int:user_id>', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def chat(job_id, user_id):
    try:
        # Fetch the relevant JobApplication (using applicant's user_id)
        job_application = JobApplication.query.filter_by(job_id=job_id, user_id=user_id).first()
        if not job_application:
            return jsonify({"error": "Job application not found"}), 404

        # Fetch the associated Job
        job = job_application.job
        if not job:
            return jsonify({"error": "Job not found"}), 404

        room = f"job_{job_id}_user_{user_id}"

        labourer_trading_name = job_application.user.company_details.trading_name if job_application.user.company_details else None
        job_poster_first_name = job.user.first_name
        applicant_profile_image = job_application.user.profile_image.filename if job_application.user.profile_image else 'orange.jpg'

        if job.image_paths:
            job_image_paths = job.image_paths.split(',')
            job_image_path = job_image_paths[0]
        else:
            job_image_path = 'default-job.jpg'

        profile_deleted_note = None
        if job_application.user.soft_deleted:
            profile_deleted_note = "The applicant's profile has been deleted."
        elif job.user.soft_deleted:
            profile_deleted_note = "The job poster's profile has been deleted."

        if request.method == 'POST':
            content = request.form.get('message')
            if not content:
                return jsonify({"error": "Message content cannot be empty"}), 400

            if current_user.id == job_application.user_id:
                receiver_id = job.user_id
            else:
                receiver_id = job_application.user_id

            message = Message(
                sender_id=current_user.id,
                receiver_id=receiver_id,
                content=content,
                job_application_id=job_application.id,
                room=room,
                timestamp=datetime.now(pytz.timezone('Pacific/Auckland'))  # ✅ Proper timestamp
            )
            db.session.add(message)
            db.session.commit()

            create_message_notification(
                receiver_id=receiver_id,
                message_content=f"New message from {current_user.first_name} regarding job '{job.job_name}'",
                job_application_id=job_application.id,
                job_id=job.id
            )

            # Email notification
            receiver_user = User.query.get(receiver_id)
            if receiver_user:
                email_subject = f"New Message Regarding Job: {job.job_name}"
                email_context = {
                    "user": receiver_user,
                    "job_title": job.job_name,
                    "message_link": f"{request.url_root}login"  # Generate message link
        }
                send_async_email(receiver_user.email, email_subject, "email/email_job_message.html", email_context)

        messages = Message.query.filter_by(job_application_id=job_application.id).order_by(Message.timestamp).all()

        nz_tz = pytz.timezone('Pacific/Auckland')
        for message in messages:
            if message.timestamp:
                message.timestamp = message.timestamp.astimezone(nz_tz)


        Message.query.filter_by(
            job_application_id=job_application.id,
            receiver_id=current_user.id,
            is_read=False
        ).update({"is_read": True})
        db.session.commit()

        return render_template(
            'chat_business.html',
            messages=messages,
            room=room,
            job_name=job.job_name,
            applicant_name=f"{job_application.user.first_name} {job_application.user.last_name}",
            labourer_trading_name=labourer_trading_name,
            job_poster_first_name=job_poster_first_name,
            job_location=job.location,
            job_id=job_id,
            user_id=job_application.user.id,
            user=current_user,
            applicant_profile_image=applicant_profile_image,
            job_image_path=job_image_path,
            profile_deleted_note=profile_deleted_note
        )

    except Exception as e:
        print(f"Error in chat route for job_id={job_id}, user_id={user_id}: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500

@app.route('/messages')
@csrf.exempt
@login_required
def messages():
    try:
        # Fetch all messages where the current user is either the sender or receiver
        messages = Message.query.filter(
            (Message.sender_id == current_user.id) | (Message.receiver_id == current_user.id)
        ).all()

        # Convert timestamp to NZST (New Zealand Standard Time)
        nz_tz = pytz.timezone('Pacific/Auckland')
        for message in messages:
            message.timestamp = message.timestamp.astimezone(nz_tz)  # Convert to local NZST

        # Group unread counts by room
        unread_counts = db.session.query(Message.room, db.func.count(Message.id)).filter(
            Message.receiver_id == current_user.id,
            Message.is_read == False
        ).group_by(Message.room).all()
        unread_map = {room: count for room, count in unread_counts}

        conversations = []  # To store conversation data

        for message in messages:
            if message.job_application_id:
                # Job-related chat
                job_application = JobApplication.query.get(message.job_application_id)
                if job_application:
                    other_user_id = job_application.user_id if current_user.business_profile else job_application.job.user_id
                    job_id = job_application.job.id

                    # Check if the conversation already exists
                    conversation = next(
                        (conv for conv in conversations if conv.get('job_application_id') == job_application.id),
                        None
                    )
                    if not conversation:
                        conversations.append({
                            'room': message.room,
                            'job_application_id': job_application.id,
                            'job_id': job_id,
                            'applicant_user_id': job_application.user_id,
                            'job_name': job_application.job.job_name,
                            'most_recent_message': message.content,
                            'timestamp': message.timestamp,
                            'other_user_id': other_user_id,
                            'is_job_chat': True,
                            'is_unread': unread_map.get(message.room, 0) > 0
                        })
                    else:
                        if message.timestamp > conversation['timestamp']:
                            conversation['most_recent_message'] = message.content
                            conversation['timestamp'] = message.timestamp
                            conversation['is_unread'] = unread_map.get(message.room, 0) > 0
            else:
                # User-to-user chat
                other_user_id = message.sender_id if message.receiver_id == current_user.id else message.receiver_id

                # Check if the conversation already exists
                conversation = next(
                    (conv for conv in conversations if conv.get('room') == message.room),
                    None
                )
                if not conversation:
                    conversations.append({
                        'room': message.room,
                        'user_id': other_user_id,
                        'most_recent_message': message.content,
                        'timestamp': message.timestamp,
                        'other_user_id': other_user_id,
                        'is_job_chat': False,
                        'is_unread': unread_map.get(message.room, 0) > 0
                    })
                else:
                    if message.timestamp > conversation['timestamp']:
                        conversation['most_recent_message'] = message.content
                        conversation['timestamp'] = message.timestamp
                        conversation['is_unread'] = unread_map.get(message.room, 0) > 0

        # Fetch user details in a single query
        user_ids = [conv['other_user_id'] for conv in conversations]
        users = User.query.filter(User.id.in_(user_ids)).all()
        user_map = {user.id: user.first_name for user in users}
        company_details_map = {user.id: user.company_details.trading_name if user.company_details else "None" for user in users}

        # Update conversations with user names and trading names
        for conv in conversations:
            conv['other_user_name'] = user_map.get(conv['other_user_id'], "Unknown")
            conv['other_user_trading_name'] = company_details_map.get(conv['other_user_id'], "None")

        # Sort conversations by the most recent message timestamp, latest message first
        conversations.sort(key=lambda conv: conv['timestamp'], reverse=True)

        # Render the template
        return render_template('messages.html', conversations=conversations, unread_map=unread_map, is_dashboard_page=True)

    except Exception as e:
        print(f"Error in messages route: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500



def create_message(sender_id, receiver_id, content, job_application_id=None, room=None):
    # Create a timezone-aware UTC datetime
    utc_time = datetime.now(pytz.utc)

    # Convert UTC time to New Zealand Standard Time (NZST) or New Zealand Daylight Time (NZDT)
    nz_tz = pytz.timezone('Pacific/Auckland')  # Handles both NZST and NZDT automatically
    local_time = utc_time.astimezone(nz_tz)

    # Create and add the message to the database
    message = Message(
        sender_id=sender_id,
        receiver_id=receiver_id,
        content=content,
        timestamp=local_time,  # Store the time in NZST or NZDT
        job_application_id=job_application_id,
        room=room,
    )
    db.session.add(message)
    db.session.commit()
def get_or_create_labourer_chat_room(user1_id, user2_id):
    """
    Creates or retrieves a chat room for two users.

    Args:
        user1_id (int): ID of the first user.
        user2_id (int): ID of the second user.

    Returns:
        str: The unique room identifier for the chat.
    """
    # Ensure the room name is consistent (e.g., smaller ID first)
    sorted_ids = sorted([user1_id, user2_id])
    room = f"user_{sorted_ids[0]}_user_{sorted_ids[1]}"
    return room

@app.route('/labourer_chat/<int:user2_id>', methods=['GET', 'POST'])
@login_required
@csrf.exempt
def labourer_chat(user2_id):
    """
    Handles labourer-to-labourer chat functionality.
    """
    try:
        # Ensure current user is a labourer
        if not current_user.labourer_profile:
            return jsonify({"error": "You are not authorized to use this feature."}), 403

        # Fetch the other user's details
        other_user = User.query.get(user2_id)
        if not other_user:
            return jsonify({"error": "The user does not exist."}), 404

        # Check if the other user's profile is soft-deleted
        profile_deleted_note = None
        if other_user.soft_deleted:
            profile_deleted_note = f"{other_user.first_name}'s profile has been deleted."

        # Get or create the chat room
        room = get_or_create_labourer_chat_room(current_user.id, user2_id)
        if not room:
            return jsonify({"error": "Chat room could not be created."}), 500

        # Handle POST request: Sending a message
        if request.method == 'POST':
            content = request.form.get('message')
            if not content:
                return jsonify({"error": "Message content cannot be empty."}), 400
            
            # Get the current time in NZST
            nz_tz = pytz.timezone('Pacific/Auckland')
            nz_now = datetime.now(nz_tz)  # Get the current time in NZST

            # Save the message
            message = Message(
                sender_id=current_user.id,
                receiver_id=user2_id,
                content=content,
                room=room,
                timestamp=nz_now
            )
            db.session.add(message)
            db.session.commit()

            # Create notification
            create_trade_message_notification(user2_id)

            # Send an email to the receiver
            receiver_user = User.query.get(user2_id)
            if receiver_user and receiver_user.email:
                email_subject = f"You Have A New Message From {current_user.first_name}"
                email_context = {
                    "receiver_first_name": receiver_user.first_name or "Valued User",
                    "sender_first_name": current_user.first_name,
                    "sender_trading_name": current_user.company_details.trading_name or "Your Company",
                    "message_link": f"{request.url_root}login"  # Replace with actual chat link if available
                }
                send_async_email(receiver_user.email, email_subject, "email/email_labourer_message.html", email_context)

        # Fetch all messages in the chat room
        messages = Message.query.filter_by(room=room).order_by(Message.timestamp).all()

        # Mark all unread messages as read for the current user
        Message.query.filter_by(room=room, receiver_id=current_user.id, is_read=False).update({"is_read": True})
        db.session.commit()

        # Render the chat page
        return render_template(
            'chat_labourer.html',
            messages=messages,
            room=room,
            profile_deleted_note=profile_deleted_note,
            other_user=other_user
        )

    except Exception as e:
        print(f"Error in labourer_chat for user2_id={user2_id}: {e}")
        return jsonify({"error": "An unexpected error occurred."}), 500

def create_trade_message_notification(user2_id):
    receiver = User.query.get(user2_id)
    if receiver:
        notification_message = f"{current_user.first_name} from {current_user.company_details.trading_name} sent you a message"
        notification = Notification(
            user_id=user2_id,
            message=notification_message,
            read=False,
            notification_type="trade_message",
            timestamp=datetime.utcnow(),
            user2_id=current_user.id  # This should be the current user's ID
        )
        db.session.add(notification)
        db.session.commit()

def time_ago(dt):
    now = datetime.utcnow()
    diff = now - dt

    seconds = diff.total_seconds()
    minutes = seconds // 60
    hours = minutes // 60
    days = hours // 24

    if seconds < 60:
        return f"{int(seconds)}s ago"
    elif minutes < 60:
        return f"{int(minutes)}m ago"
    elif hours < 24:
        return f"{int(hours)}h ago"
    else:
        return f"{int(days)}d ago"
    
app.jinja_env.filters['time_ago'] = time_ago

@app.route('/my_jobs_display_job/<int:job_id>')
@login_required
def my_job_display_job(job_id):
    job = Job.query.get_or_404(job_id)


    return render_template('my_job_display_job.html', job=job,)

from flask import request, jsonify, redirect, url_for
import os
from werkzeug.utils import secure_filename

@app.route('/upload_id_image', methods=['POST'])
@csrf.exempt
@login_required
def upload_id_image():
    if 'id_image' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['id_image']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    allowed_extensions = {'png', 'jpg', 'jpeg'}

    if '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
        filename = secure_filename(file.filename)
        upload_folder = os.path.join(app.root_path, 'static', 'id_images')
        os.makedirs(upload_folder, exist_ok=True)  # Create the folder if it doesn't exist
        upload_path = os.path.join(upload_folder, filename)
        file.save(upload_path)

        # Append to the existing ID image path
        current_images = current_user.labourer_profile.id_image
        if current_images:
            updated_images = ','.join([current_images, filename])  # Add new file to existing paths
        else:
            updated_images = filename  # First file upload

        current_user.labourer_profile.id_image = updated_images

        # Check if the user is already ID verified, and if so, set verification_ready to True
        if current_user.labourer_profile.id_verified:
            current_user.labourer_profile.verification_ready = True

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"Database error: {str(e)}"}), 500

        return jsonify({"message": "ID Image uploaded successfully!"}), 200
    else:
        return jsonify({"error": "Invalid file format. Only PNG, JPG, and JPEG are allowed."}), 400

@app.route('/upload_liability_insurance', methods=['POST'])
@csrf.exempt
@login_required
def upload_liability_insurance():
    if 'liability_insurance' not in request.files:
        return jsonify({"error": "No file part"}), 400

    files = request.files.getlist('liability_insurance')

    if not files or all(file.filename == '' for file in files):
        return jsonify({"error": "No selected files"}), 400

    allowed_extensions = {'png', 'jpg', 'jpeg', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'odt', 'ods', 'txt'}

    if not current_user.labourer_profile:
        return jsonify({"error": "Labourer profile not found"}), 400

    # Save the files and store paths
    file_paths = []
    for file in files:
        if file and '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.root_path,'static', 'insurance_images', filename)
            file.save(file_path)
            file_paths.append(filename)
        else:
            return jsonify({"error": "Invalid file format. Only images and PDFs are allowed."}), 400

    # Append new file paths to the existing ones
    current_files = current_user.labourer_profile.insurance_image
    if current_files:
        updated_files = ','.join([current_files] + file_paths)  # Append new files to existing
    else:
        updated_files = ','.join(file_paths)  # First upload

    current_user.labourer_profile.insurance_image = updated_files

    # Check if the user is ID verified, and if so, set verification_ready to True
    if current_user.labourer_profile.id_verified:
        current_user.labourer_profile.verification_ready = True

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Database error: {str(e)}"}), 500

    return jsonify({"message": "Liability insurance uploaded successfully!"}), 200



@app.route('/reviews/<int:user_id>')
@csrf.exempt
def reviews_page(user_id):
    user = User.query.get_or_404(user_id)  # Fetch user by ID
    # Fetch all reviews for the user and join with the Job table to get job details
    reviews = db.session.query(Review, Job).join(Job, Job.id == Review.job_id).filter(Review.user_id == user_id).all()

    for review, job in reviews:
        job.formatted_date = job.date_created.strftime("%B %d, %Y")  # Example: January 13, 2025
    
    return render_template('reviews.html', reviews=reviews, user=user)

def calculate_overall_rating(user):
    reviews = user.reviews  # Assuming `reviews` is a relationship in the User model
    if not reviews:
        return 0  # No reviews yet

    total_score = 0
    for review in reviews:
        avg_review_score = (review.professionalism + review.quality + review.cost + review.communication) / 4
        total_score += avg_review_score

    overall_rating = total_score / len(reviews)
    return round(overall_rating, 2)  # Round to 2 decimal places

@app.route('/delete_account', methods=['POST' , 'GET'])
@csrf.exempt
def delete_account():
    # Get the current user (assuming they are logged in)
    user = current_user  # or however you're retrieving the user

    # Mark the user as soft deleted
    user.soft_deleted = True
    db.session.commit()

    flash('Your account has been deactivated.', 'success')
    return redirect(url_for('login'))  # Or wherever the user should be redirected






@app.route('/change-email', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def change_email():
    if request.method == 'POST':
        new_email = request.form.get('new_email')
        password = request.form.get('password')

        # Verify the password using bcrypt
        if not bcrypt.check_password_hash(current_user.password, password):
            flash('Incorrect password. Please try again.', 'danger')
            return redirect(url_for('change_email'))

        # Update the user's email
        current_user.email = new_email
        db.session.commit()
        flash('Your email has been updated successfully.', 'success')
        return redirect(url_for('business_profile'))

    return render_template('business_profile.html')





@app.route('/change-password', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # Verify current password
        if not bcrypt.check_password_hash(current_user.password, current_password):
            flash('Incorrect current password. Please try again.', 'danger')
            return redirect(url_for('business_profile'))

        # Check if new passwords match
        if new_password != confirm_password:
            flash('Passwords do not match. Please try again.', 'danger')
            return redirect(url_for('business_profile'))

        # Update password
        current_user.password = bcrypt.generate_password_hash(new_password)
        db.session.commit()
        flash('Your password has been updated successfully.', 'success')
        return redirect(url_for('business_profile'))

    return render_template('business_profile.html')

@app.route('/save_location', methods=['POST'])
@csrf.exempt
@login_required
def save_location():
    location = request.form.get('location')
    if location:
        # Save the location to the user's profile or relevant model
        current_user.location = location  # Assuming the `location` field exists on your user model
        db.session.commit()
        flash(f'Your location has been updated to {location}.', 'success')
    else:
        flash('Please select a valid location.', 'error')
    return redirect(url_for('business_profile'))  # Replace with your appropriate redirect

@app.route('/labourer-change-email', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def labourer_change_email():
    if request.method == 'POST':
        new_email = request.form.get('new_email')
        password = request.form.get('password')

        # Verify the password
        if not bcrypt.check_password_hash(current_user.password, password):
            flash('Incorrect password. Please try again.', 'danger')
            return redirect(url_for('labourer_profile'))

        # Update email
        current_user.email = new_email
        db.session.commit()
        flash('Your email has been updated successfully.', 'success')
        return redirect(url_for('labourer_profile'))  # Redirect to labourer profile

    return render_template('labourer_profile.html')  # Render the labourer profile page


@app.route('/labourer-change-password', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def labourer_change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # Verify current password
        if not bcrypt.check_password_hash(current_user.password, current_password):
            flash('Incorrect current password. Please try again.', 'danger')
            return redirect(url_for('labourer_profile'))

        # Check if new passwords match
        if new_password != confirm_password:
            flash('New passwords do not match. Please try again.', 'danger')
            return redirect(url_for('labourer_profile'))

        # Update password
        current_user.password = bcrypt.generate_password_hash(new_password)
        db.session.commit()
        flash('Your password has been updated successfully.', 'success')
        return redirect(url_for('labourer_profile'))  # Redirect to labourer profile

    return render_template('labourer_profile.html')  # Render the labourer profile page


@app.route('/labourer-save-location', methods=['POST'])
@csrf.exempt
@login_required
def labourer_save_location():
    location = request.form.get('location')
    if location:
        # Save the location to the user's profile or relevant model
        current_user.location = location  # Assuming the `location` field exists on your user model
        db.session.commit()
        flash(f'Your location has been updated to {location}.', 'success')
    else:
        flash('Please select a valid location.', 'error')
    return redirect(url_for('labourer_profile'))  # Redirect to labourer profile

from functools import wraps
from flask import abort

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin', methods=['GET'])
@csrf.exempt
@login_required
@admin_required
def admin_dashboard():
    total_job_contacts = db.session.query(func.count(JobApplication.id)).scalar()
    homeowner_users = User.query.join(BusinessProfile).all()
    tradesman_users = User.query.join(LabourerProfile).all()
    users = User.query.all()
    jobs = Job.query.all()  # Assuming you have a Job model
    pending_verifications = User.query.filter(
        User.labourer_profile.has(
            LabourerProfile.verification_ready == True
        )
    ).all()

    return render_template('admin_dashboard.html', users=users, jobs=jobs, pending_verifications=pending_verifications, tradesman_users=tradesman_users,total_job_contacts=total_job_contacts,homeowner_users=homeowner_users)

@app.route('/admin/user/<int:user_id>', methods=['GET', 'POST'])
@csrf.exempt
@login_required
@admin_required
def admin_user_details(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        if 'verify' in request.form:
            user.id_verified = True
            db.session.commit()
            flash(f"{user.email}'s ID has been verified.", 'success')
        elif 'deactivate' in request.form:
            user.is_active = False
            db.session.commit()
            flash(f"{user.email} has been deactivated.", 'warning')
    return render_template('admin_user_details.html', user=user)

@app.route('/verify-profile', methods=['POST'])
@csrf.exempt
@login_required
def verify_profile():
    confirmation = request.form.get('confirmation')
    if confirmation:
        # Set the verification_ready flag to True
        current_user.labourer_profile.verification_ready = True
        current_user.labourer_profile.company_details_locked = True
        db.session.commit()
        flash('Your profile has been marked as complete and is ready for validation.', 'success')
    else:
        flash('Please confirm that your information is correct.', 'error')
    return redirect(url_for('labourer_profile'))

@app.route('/update_verification/<int:user_id>', methods=['POST'])
@csrf.exempt
@login_required
@admin_required
def update_verification(user_id):
    user = User.query.get_or_404(user_id)

    # Get checkbox values from the form
    id_verified = request.form.get('id_verified') == 'true'
    insurance_verified = request.form.get('insurance_verified') == 'true'

    # Update the labourer profile with verification statuses
    user.labourer_profile.id_verified = id_verified
    user.labourer_profile.insurance_verified = insurance_verified
    db.session.commit()  # Commit changes to the database

    # Determine email content based on verification status
    if id_verified:
        # ID verified, check insurance status
        subject = 'Your Profile Has Been Verified!'
        insurance_uploaded = insurance_verified
        email_template = 'email/verified_profile.html'

        user.labourer_profile.verification_ready = False
    else:
        # ID not verified
        subject = 'Verification Unsuccessful'
        insurance_uploaded = None
        email_template = 'email/verification_failed.html'

        user.labourer_profile.verification_ready = False
        user.labourer_profile.company_details_locked = False

    db.session.commit()  # Commit changes to the database




    # Create and send the email
    msg = emailmessage(subject, recipients=[user.email])
    msg.html = render_template(email_template, user=user, insurance_uploaded=insurance_uploaded)

    try:
        mail.send(msg)
        flash("Verification email sent to the user.", "success")
    except Exception as e:
        flash(f"Failed to send verification email: {str(e)}", "danger")

    # Redirect back to the admin dashboard
    return redirect(url_for('admin_dashboard'))

@app.route('/impersonate/<int:user_id>', methods=['GET'])
@csrf.exempt
@login_required
def impersonate(user_id):
    for rule in app.url_map.iter_rules():
        print(rule)

    # Check if the current user is an admin
    if not current_user.is_admin:
        flash("You are not authorized to impersonate users.")
        return redirect(url_for('login'))

    user_to_impersonate = User.query.get(user_id)
    if not user_to_impersonate:
        flash("User not found.")
        return redirect(url_for('admin_dashboard'))

    # Store admin's ID in the session to revert later
    session['admin_id'] = current_user.id
    session['is_impersonating'] = True

    # Log in as the target user
    login_user(user_to_impersonate)
    flash(f"You are now impersonating {user_to_impersonate.first_name}.")

    # Redirect based on the user type (homeowner or labourer)
    if hasattr(user_to_impersonate, 'business_profile') and user_to_impersonate.business_profile:
        # If the user has a business profile (homeowner)
        return redirect(url_for('business_profile'))  # Redirect to the homeowner's dashboard (or another page for business users)
    
    elif hasattr(user_to_impersonate, 'labourer_profile') and user_to_impersonate.labourer_profile:
        # If the user has a labourer profile (labourer)
        return redirect(url_for('labourer_profile'))  # Redirect to the labourer's dashboard (or another page for labourers)

    
    # Default fallback in case the user type is unrecognized
    flash("Unable to impersonate the selected user.")
    return redirect(url_for('admin_dashboard'))

@app.route('/end_impersonation', methods=['POST'])
@csrf.exempt
def end_impersonation():
    # Ensure the session contains impersonation data
    if not session.get('is_impersonating'):
        flash("You are not impersonating any user.")
        return redirect(url_for('dashboard'))

    # Get the admin's ID from the session
    admin_id = session.pop('admin_id', None)
    session.pop('is_impersonating', None)

    # Log the admin back in
    if admin_id:
        admin = User.query.get(admin_id)
        if admin:
            login_user(admin)
            flash("You have ended impersonation and are now back to your admin account.")
            return redirect(url_for('admin_dashboard'))

    flash("Unable to revert to admin account.")
    return redirect(url_for('login'))

@app.route('/admin_tradesman', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def admin_tradesman():
    if not current_user.is_admin:
        flash("You are not authorized to view this page.")
        return redirect(url_for('dashboard'))

    # Get search query from request
    search_query = request.args.get('search', '').strip()

    # Query all tradesmen, including location and email fields
    if search_query:
        tradesman_users = User.query.filter(
            User.labourer_profile != None,
            (
                User.first_name.ilike(f"%{search_query}%") |
                User.last_name.ilike(f"%{search_query}%") |
                User.location.ilike(f"%{search_query}%") |  # Added location search
                User.email.ilike(f"%{search_query}%")      # Added email search
            )
        ).all()
    else:
        tradesman_users = User.query.filter(User.labourer_profile != None).all()

    return render_template('admin_tradesman.html', tradesman_users=tradesman_users, search_query=search_query)

from sqlalchemy import or_

@app.route('/admin_homeowners')
@csrf.exempt
@login_required
def admin_homeowners():
    if not current_user.is_admin:
        flash("You are not authorized to view this page.")
        return redirect(url_for('login'))  # Redirect to admin dashboard if not authorized

    search = request.args.get('search', '')  # Get the search term from the URL, default to empty string if not provided

    # Query all users who have a business profile (business users)
    homeowners = User.query.filter(User.business_profile != None)

    if search:
        homeowners = homeowners.filter(
            or_(
                User.first_name.ilike(f'%{search}%'),
                User.last_name.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%'),
                User.location.ilike(f"%{search}%") 
            )
        )

    homeowners = homeowners.all()

    # Fetch all open jobs (if any) associated with each homeowner's business profile
    homeowners_with_jobs = []
    for homeowner in homeowners:
        open_jobs = Job.query.filter_by(business_profile_id=homeowner.business_profile.id, status='open').all()
        homeowners_with_jobs.append({
            'user': homeowner,
            'open_jobs': open_jobs
        })

    return render_template('admin_homeowners.html', homeowners_with_jobs=homeowners_with_jobs, search=search)

@app.route('/admin_jobs')
@csrf.exempt
def admin_jobs():
    search = request.args.get('search', '')  # Get the search term from the URL, default to empty string if not provided

    # Query all jobs from the database
    jobs = Job.query.join(User).filter(
        (User.first_name.ilike(f'%{search}%')) |
        (User.last_name.ilike(f'%{search}%')) |
        (User.email.ilike(f'%{search}%'))  |
        (Job.location.ilike(f'%{search}%'))       
    ).all()

    return render_template('admin_jobs.html', jobs=jobs, search=search)

@app.route('/routes')
def list_routes():
    import urllib
    output = []
    for rule in app.url_map.iter_rules():
        methods = ','.join(rule.methods)
        line = urllib.parse.unquote(f"{rule.endpoint}: {rule.rule} [{methods}]")
        output.append(line)
    return "<br>".join(output)

@app.route('/preview_email')
def preview_email():
    user = {
        'first_name': 'John',  # Example user data
    }
    return render_template('verified_profile.html', user=user)

@app.route('/homeowner_index')
def homeowner_index():
    return render_template('homeowner_index.html')

@app.route('/find_equipment')
def find_equipment():
    # Query to get all equipment posts from the database
    equipment_posts = GearPost.query.all()

    # Loop through each post and split the comma-separated image URLs
    for post in equipment_posts:
        print(f"Original image_url for post {post.id}: {post.image_url}")  # Debug print
        
        # If image_url exists, split by commas, and make sure the path is clean
        if post.image_url:
            post.images = [image.replace('/static', '') for image in post.image_url.split(',')]  # Strip '/static' and split
            # Remove 'rental_images/' from the image paths if it exists
            post.images = [image.lstrip('rental_images/') for image in post.images]
        else:
            post.images = []

        print(f"Images list for post {post.id}: {post.images}")  # Debug print

    # Pass the posts to the template
    return render_template('find_equipment.html', equipment_posts=equipment_posts)

@app.route('/create_equipment_listing', methods=['GET', 'POST'])
def create_equipment_listing():
    if request.method == 'POST':
        # Get form data
        equipment_name = request.form.get('equipment_name')
        category = request.form.get('category')
        location = request.form.get('location')
        city_suburb = request.form.get('city_suburb')
        description = request.form.get('description')
        pickup_only = 'pickup_only' in request.form  # If it's checked
        delivery_available = 'delivery_available' in request.form  # If it's checked
        bond_required = 'bond_required' in request.form  # If it's checked
        bond_amount = request.form.get('bond_amount') if bond_required else None

        # Handle price fields - convert to float if not empty, otherwise None
        price = request.form.get('price')
        price_per_day = request.form.get('price_day')
        price_per_week = request.form.get('price_week')
        price_per_half_day = request.form.get('price_half_day')

        # Convert empty strings to None for float fields
        price = float(price) if price else None
        price_per_day = float(price_per_day) if price_per_day else None
        price_per_week = float(price_per_week) if price_per_week else None
        price_per_half_day = float(price_per_half_day) if price_per_half_day else None

        rental_duration = request.form.get('rental_duration')

        # Handle file upload (if images are being uploaded)
        images = request.files.getlist('images')
        image_urls = []  # Will store the URLs of uploaded images

        # Define the path for saving images in the static folder
        upload_folder = os.path.join(app.root_path, 'static', 'rental_images')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)  # Create the folder if it doesn't exist

        # Process the uploaded images and save them in the rental_images folder
        for image in images:
            if image:
                filename = secure_filename(image.filename)  # Secure the filename
                image_path = os.path.join(upload_folder, filename)  # Full path for saving
                image.save(image_path)  # Save the image

                # Generate URL for the image
                image_url = f'/static/rental_images/{filename}'
                image_urls.append(image_url)  # Add the image URL to the list

        # Create a new GearPost object
        new_post = GearPost(
            user_id=current_user.id,  # Assuming you're using Flask-Login to get the current user
            title=equipment_name,
            equipment_type=category,
            location=location,
            city_suburb=city_suburb,
            description=description,
            is_rental=True,  # Assuming it’s always rental
            price=price,
            price_per_day=price_per_day,
            price_per_week=price_per_week,
            price_per_half_day=price_per_half_day,
            rental_duration=rental_duration,
            image_url=','.join(image_urls),  # Store the image URLs as a comma-separated string
            pickup_only=pickup_only,
            delivery_available=delivery_available,
            bond_required=bond_required,
            bond_amount=bond_amount
        )

        # Add the new post to the session and commit to the database
        db.session.add(new_post)
        db.session.commit()

        flash("Equipment listing created successfully!", "success")  # Optional message
        return redirect(url_for('find_equipment'))  # Redirect after successful submission

    return render_template('create_equipment_listing.html')

@app.route('/edit_job/<int:job_id>', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def edit_job(job_id):
    job = Job.query.get_or_404(job_id)

    # Ensure that the current user is the owner of the job
    if job.business_profile.user_id != current_user.id:
        flash("You do not have permission to edit this job.", "error")
        return redirect(url_for('business_created_jobs'))

    if request.method == 'POST':
        # Update job details based on the form submission
        job.job_name = request.form['job_name']
        job.job_category = request.form['job-category']
        job.location = request.form.get('location')
        job.city = request.form['city']
        job.suburb = request.form['suburb']
        job.tasks = request.form['tasks']
        job.additional_details = request.form.get('additional-details')
        job.contact_number = request.form.get('contact_number')

        # Handle image uploads
        image_paths = []

        # Ensure the directory exists
        image_dir = os.path.join(app.root_path, 'static', 'job_images')
        if not os.path.exists(image_dir):
            os.makedirs(image_dir)

        # Get the uploaded images
        if 'photo-upload' in request.files:
            photo_uploads = request.files.getlist('photo-upload')

            for photo_upload in photo_uploads:
                if photo_upload.filename != '':  # Ensure there's a filename
                    filename = secure_filename(photo_upload.filename)
                    file_path = os.path.join(image_dir, filename)
                    photo_upload.save(file_path)
                    image_paths.append(filename)

        # Retain existing images if no new images are uploaded
        if job.image_paths:
            # Add the existing image paths (if any)
            existing_images = job.image_paths.split(',')
            image_paths.extend(existing_images)

        # Update image paths in the database (update if images exist, else set to None)
        job.image_paths = ','.join(image_paths) if image_paths else None

        # Commit changes to the database
        db.session.commit()

        flash("Job updated successfully!", "success")
        return redirect(url_for('business_created_jobs'))

    # Pass the image_paths attribute to the template
    return render_template('edit_job.html', job=job, image_paths=job.image_paths.split(',') if job.image_paths else [])


@app.route('/remove_job_image', methods=['DELETE'])
@csrf.exempt
def remove_job_image():
    # Parse incoming JSON data from the request
    data = request.get_json()
    image_filename = data.get('image_filename')
    job_id = data.get('job_id')  # Get job ID from request

    # Debugging print statements for verification
    print("DEBUG: Received request to remove job image")
    print(f"DEBUG: image_filename = {image_filename}")
    print(f"DEBUG: job_id = {job_id}")

    # Check if the necessary data was provided
    if not image_filename or not job_id:
        print("ERROR: Missing required data")
        return jsonify({"success": False, "message": "Missing required data"}), 400

    # Delete the image file from the file system
    upload_folder = os.path.join('static', 'job_images')  # Correct folder for job images
    file_path = os.path.join(upload_folder, image_filename)

    if os.path.exists(file_path):
        os.remove(file_path)  # Delete the image
        print(f"DEBUG: Successfully deleted {file_path}")
    else:
        print("ERROR: Image file not found on server")
        return jsonify({"success": False, "message": "Image file not found"}), 404

    # Update the database to remove the image from the job's image list
    job = Job.query.get(job_id)  # Query the job by ID
    if job:
        # Get the list of images and remove the specified image
        job_images = job.image_paths.split(',') if job.image_paths else []
        if image_filename in job_images:
            job_images.remove(image_filename)
            job.image_paths = ','.join(job_images) if job_images else None
            db.session.commit()  # Commit the changes to the database
            print("DEBUG: Updated database successfully")
        else:
            print("ERROR: Image filename not found in database")
            return jsonify({"success": False, "message": "Image not found in job data"}), 404
    else:
        print("ERROR: Job not found in database")
        return jsonify({"success": False, "message": "Job not found"}), 404

    # Return a success response
    return jsonify({"success": True})


@app.route('/start_payment/<int:job_id>')
@login_required
def start_payment(job_id):
    job = Job.query.get_or_404(job_id)

    stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

    try:
        # Create the Stripe Checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'nzd',  # Currency for the payment
                    'unit_amount': 500,  # $5.00 in cents
                    'product_data': {
                        'name': f"Application for job: {job.job_name}",
                    },
                },
                'quantity': 1,
            }],
            mode='payment',
            metadata={
                'user_id': current_user.id,
                'job_id': job.id,
            },
            success_url=f"{request.url_root}payment_success?session_id={{CHECKOUT_SESSION_ID}}",  # Redirect URL after successful payment
            cancel_url=f"{request.url_root}job/{job.id}",  # Redirect URL if the user cancels the payment
        )

        return redirect(checkout_session.url)

    except Exception as e:
        flash(f"Payment setup failed: {str(e)}", "danger")
        return redirect(url_for('display_job', job_id=job.id))


@app.route('/stripe_webhook', methods=['POST'])
@csrf.exempt
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
    event = None
  


    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError as e:
        return jsonify({"error": "Invalid payload"}), 400
    except stripe.error.SignatureVerificationError as e:
        return jsonify({"error": "Invalid signature"}), 400

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        metadata = session.get('metadata', {})

        user_id = int(metadata.get('user_id'))
        job_id = int(metadata.get('job_id'))

        if not user_id or not job_id:
            return jsonify({'error': 'Missing metadata'}), 400

        job = Job.query.get(job_id)
        user = User.query.get(user_id)

        if not job or not user:
            return jsonify({'error': 'Job or user not found'}), 404

        # Check if user has already applied
        application = JobApplication.query.filter_by(user_id=user.id, job_id=job.id).first()

        if application:
            application.status = 'paid'  # Update status if the application exists
        else:
            application = JobApplication(user_id=user.id, job_id=job.id, status='paid')
            db.session.add(application)

        db.session.commit()

        # Notify the job poster (via notification system)
        create_job_application_notification(
            receiver_id=job.user_id,
            job_id=job.id,
            trading_name=user.company_details.trading_name,
            applicant_name=user.first_name
        )

        # Prepare email context and send email
        email_context = {
            "job_poster_name": job.user.first_name,
            "job_title": job.job_name,
            "applicant_name": user.first_name,
            "trading_name": user.company_details.trading_name,
            "message_link": f"{request.url_root}login"
        }

        send_async_email(
            to=job.user.email,
            subject=f"New Application for '{job.job_name}'",
            template_name="email/job_application_notification.html",
            context=email_context
        )

    return jsonify({'status': 'success'}), 200


@app.route('/payment_success')
@login_required
def payment_success():
    session_id = request.args.get('session_id')

    # Retrieve the session from Stripe using the session_id
    session = stripe.checkout.Session.retrieve(session_id)

    # Get user ID and job ID from the session metadata
    user_id = int(session.metadata['user_id'])
    job_id = int(session.metadata['job_id'])

    # Ensure application is marked as paid (this should already be handled in the webhook, but we can do it here for safety)
    job_application = JobApplication.query.filter_by(user_id=user_id, job_id=job_id).first()
    if job_application and job_application.status != 'paid':
        job_application.status = 'paid'
        db.session.commit()

    flash("Payment successful! You've applied for the job.", "success")
    return redirect(url_for('applied_jobs'))



@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory('static', 'sitemap.xml')

@app.route('/robots.txt')
def robots_txt():
    return (
        "User-agent: *\n"
        "Disallow:\n"
        "Sitemap: https://www.openwork.co.nz/sitemap.xml\n",
        200,
        {'Content-Type': 'text/plain'}
    )


if __name__ == "__main__":
  
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)


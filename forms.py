from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed  # Import FileField and FileAllowed
from wtforms import StringField, DateField, TextAreaField, SubmitField  # Import other form fields as needed
from wtforms.validators import DataRequired  # Import validators as needed



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


class EditLabourerProfileForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    date_of_birth = DateField('Date of Birth', format='%Y-%m-%d', validators=[DataRequired()])
    phone_number = StringField('Phone Number', validators=[DataRequired()])
    user_blurb = StringField('User', validators=[DataRequired()])

    submit = SubmitField('Save Changes')
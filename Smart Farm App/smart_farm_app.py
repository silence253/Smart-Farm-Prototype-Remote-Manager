from flask import Flask, jsonify, request, render_template, url_for, redirect, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, set_access_cookies, unset_jwt_cookies
from datetime import datetime
import pytz
from flask_cors import CORS


app = Flask(__name__)
CORS(app)


# Unified Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:@localhost/smart_farm_app'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'thisisasecretkey'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)  # Initialize JWT Manager


# Login Manager Setup (Although we are using JWT, we still need this for user-related features like logout)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# User Authentication Models and Forms
@login_manager.user_loader # Call back user objects from the user ID
def load_user(user_id):
    return User.query.get(int(user_id))


# User Data model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)


# Flask WTForms
class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})
    submit = SubmitField('Register')

    def validate_username(self, username):
        # Query the database, check if the entered username is already existed in the database
        existing_user_username = User.query.filter_by(username=username.data).first()
        if existing_user_username:
            raise ValidationError('That username already exists. Please choose a different one.')


# Flask WTForms
class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})
    submit = SubmitField('Login')


def gmt7_now():
    return datetime.now(pytz.timezone('Asia/Bangkok'))


# Smart Farm Data Model
class SmartFarmData(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    parameter = db.Column(db.String(50), nullable=False, unique=True)
    unit = db.Column(db.String(20), nullable=False)
    value = db.Column(db.String(50), nullable=True)
    updated_time = db.Column(db.DateTime, default=gmt7_now, onupdate=gmt7_now)


# Plant Data Model
class PlantData(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    parameter = db.Column(db.String(50), nullable=False, unique=True)
    unit = db.Column(db.String(20), nullable=True)
    value = db.Column(db.String(50), nullable=True)


# Set up database function
def setup_database():
    """Initializes the database and populates default values if the table is empty."""
    with app.app_context():
        db.create_all()
        # Initialize Smart Farm Data
        if SmartFarmData.query.count() == 0:
            initial_data = [
                {"parameter": "temperature", "unit": "degree Celsius", "value": None},
                {"parameter": "humidity", "unit": "percent", "value": None},
                {"parameter": "co2_concentration", "unit": "ppm", "value": None},
                {"parameter": "light_intensity", "unit": "lux", "value": None},
            ]
            for item in initial_data:
                new_entry = SmartFarmData(**item)
                db.session.add(new_entry)
            db.session.commit()
            
        # Initialize Plant Data
        if PlantData.query.count() == 0:
            initial_data = [
                {"parameter": "name", "unit": None, "value": None},
                {"parameter": "species", "unit": None, "value": None},
                {"parameter": "category", "unit": None, "value": None},
                {"parameter": "optimal_temperature", "unit": "degree Celsius", "value": None},
                {"parameter": "optimal_humidity", "unit": "percent", "value": None},
                {"parameter": "optimal_co2_concentration", "unit": "ppm", "value": None},
                {"parameter": "optimal_light_intensity", "unit": "lux", "value": None},
            ]
            for item in initial_data:
                new_entry = PlantData(**item)
                db.session.add(new_entry)
            db.session.commit()    
        


# Control the Smart Farm prototype function
def update_parameter(parameter_name):
    # Query the database, check if the parameter is existed or not
    data_entry = SmartFarmData.query.filter_by(parameter=parameter_name).first()
    
    # If not existed
    if not data_entry:
        return jsonify({
            "status": "error",
            "message": f"Parameter '{parameter_name}' not found."
        }), 404

    #If existed, POST a JSON file to update the data of that paremeter
    incoming_data = request.get_json()
    if 'value' not in incoming_data:
        return jsonify({
            "status": "error",
            "message": "No value provided in the request."
        }), 400

    data_entry.value = incoming_data['value']
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": f"{parameter_name.replace('_', ' ').capitalize()} updated successfully.",
        "data": {
            "parameter": data_entry.parameter,
            "unit": data_entry.unit,
            "value": data_entry.value
        }
    }), 200



# JWT Authentication API routes

@app.route('/')
def home():
    response = {
        "status": "success",
        "message": "Welcome to the Home Page."
    }
    return jsonify(response)


@app.route('/login', methods=['POST'])
def login():
    # Parse JSON data from the request body
    data = request.get_json()

    # Extract username and password from the parsed data
    username = data.get('username')
    password = data.get('password')

    # Check if both username and password are provided
    if not username or not password:
        return jsonify({
            "status": "error",
            "message": "Username and password are required."
        }), 400

    # Query the database for the user
    user = User.query.filter_by(username=username).first()

    # Verify the user's existence and password
    if user and bcrypt.check_password_hash(user.password, password):
        # Generate JWT token
        access_token = create_access_token(identity=user.username)
        login_user(user)

        return jsonify({
            "status": "success",
            "message": "Login successful.",
            "token": access_token
        }), 200

    # If authentication fails
    return jsonify({
        "status": "error",
        "message": "Invalid username or password."
    }), 401


@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    response = {
        "status": "success",
        "message": "Welcome to the Dashboard."
    }
    return jsonify(response)


@app.route('/register', methods=['POST'])
def register():
    # Parse JSON data
    if request.is_json:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        # Validate username
        if not username or len(username) < 4 or len(username) > 20:
            return jsonify({"status": "error", "message": "Invalid username length."}), 400

        # Validate password
        if not password or len(password) < 8 or len(password) > 20:
            return jsonify({"status": "error", "message": "Invalid password length."}), 400

        # Check if username already exists
        if User.query.filter_by(username=username).first():
            return jsonify({"status": "error", "message": "Username already exists."}), 400

        # Hash the password and create a new user
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        return jsonify({"status": "success", "message": "Registration successful."}), 201

    return jsonify({"status": "error", "message": "Invalid request format."}), 400


@app.route('/logout', methods=['POST'])
@login_required
def logout():
    # Create a response object with a success message
    response = jsonify({
        "status": "success",
        "message": "Logout successful."
    })
    # Unset the JWT cookies in the response
    unset_jwt_cookies(response)
    # Log out the user
    logout_user()
    return response, 200



# Smart Farm Data API Routes

@app.route('/data_retrieval', methods=['GET'])
# @jwt_required()  # Protect this route with JWT authentication
def data_retrieval():
    # Retrieve all Smart Farm data from the database
    all_data = SmartFarmData.query.all()
    response = {
        "status": "success",
        "data": [{"parameter": item.parameter, "unit": item.unit, "value": item.value} for item in all_data]
    }
    return jsonify(response)


@app.route('/data_simulation', methods=['POST'])
@jwt_required()
def data_simulation():
    # Update Smart Farm data based on input JSON
    incoming_data = request.get_json()
    for key, value in incoming_data.items():
        # Find the corresponding entry in the database
        data_entry = SmartFarmData.query.filter_by(parameter=key).first()
        if data_entry:
            # Update the value
            data_entry.value = value
    db.session.commit()

    # Retrieve updated data for response
    updated_data = SmartFarmData.query.all()
    response = {
        "status": "success",
        "message": "Smart Farm data updated successfully!",
        "data": [{"parameter": item.parameter, "unit": item.unit, "value": item.value} for item in updated_data]
    }
    return jsonify(response)


@app.route('/update_temperature', methods=['POST'])
@jwt_required()
def update_temperature():
    return update_parameter('temperature')


@app.route('/update_humidity', methods=['POST'])
@jwt_required()
def update_humidity():
    return update_parameter('humidity')


@app.route('/update_co2_concentration', methods=['POST'])
@jwt_required()
def update_co2_concentration():
    return update_parameter('co2_concentration')


@app.route('/update_light_intensity', methods=['POST'])
@jwt_required()
def update_light_intensity():
    return update_parameter('light_intensity')


@app.route('/update_color', methods=['POST'])
@jwt_required()
def update_color():
    return update_parameter('color')



# Serve static file function
@app.route('/static/iot/templates/<path:path>')
def send_report(path):
    # Using request args for path will expose you to directory traversal attacks
    return send_from_directory('./static/iot/templates', path)



if __name__ == '__main__':
    setup_database()  # Initialize the database
    app.run(debug=True)
    
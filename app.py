from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

# Initialize the Flask application
app = Flask(__name__)

# Configuration for the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///enrollment.db'
app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with a secure key in production

# Initialize database and login manager
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Initialize Flask-Admin
admin = Admin(app)

# Define User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50))  # Can be 'student', 'teacher', or 'admin'

# Define Course model
class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(10), unique=True, nullable=False)
    course_name = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    teacher = db.Column(db.String(100), nullable=True)
    time = db.Column(db.String(50), nullable=True)
    enrolled_count = db.Column(db.Integer, default=0)

# Define Enrollment model
class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    grade = db.Column(db.String(2))

# Admin setup (Add views to manage models in the admin interface)
admin.add_view(ModelView(User, db.session))
admin.add_view(ModelView(Course, db.session))
admin.add_view(ModelView(Enrollment, db.session))

# User loader function
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Home route
@app.route('/')
def home():
    return "<h1>Welcome to the Student Enrollment Web App</h1><p>Please log in to access your courses.</p>"

# Route to display the login page and handle login logic
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get form data
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Query the user from the database
        user = User.query.filter_by(username=username).first()
        
        # Check if the user exists and the password is correct
        if user and user.password == password:  # In production, use hashed passwords
            login_user(user)
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next')
            
            # Redirect to the next page or a default page
            if next_page:
                return redirect(next_page)
            else:
                return redirect(url_for('student_courses'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

# Student route to view all available courses
@app.route('/student/courses')
@login_required
def student_courses():
    if current_user.role != 'student':
        flash("Access denied: Only students can view this page.", "danger")
        return redirect(url_for('home'))
    
    courses = Course.query.all()
    
    # Get a list of course IDs the current user is enrolled in
    enrolled_course_ids = [enrollment.course_id for enrollment in Enrollment.query.filter_by(user_id=current_user.id).all()]
    
    return render_template('student_courses.html', courses=courses, enrolled_course_ids=enrolled_course_ids)

# Student route to view enrolled courses
@app.route('/student/my_courses')
@login_required
def my_courses():
    if current_user.role != 'student':
        flash("Access denied: Only students can view this page.", "danger")
        return redirect(url_for('home'))
    
    # Get courses that the current user is enrolled in
    enrollments = Enrollment.query.filter_by(user_id=current_user.id).all()
    enrolled_courses = [Course.query.get(enrollment.course_id) for enrollment in enrollments]
    return render_template('my_courses.html', courses=enrolled_courses)

# Route for enrolling in a course
@app.route('/enroll/<int:course_id>')
@login_required
def enroll(course_id):
    if current_user.role != 'student':
        flash("Access denied: Only students can enroll in courses.", "danger")
        return redirect(url_for('home'))
    
    # Check if the student is already enrolled in this course
    existing_enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first()
    if existing_enrollment:
        flash("You are already enrolled in this course.", "info")
    else:
        # Create a new enrollment
        new_enrollment = Enrollment(user_id=current_user.id, course_id=course_id)
        db.session.add(new_enrollment)

        # Increment the enrolled_count for the course
        course = Course.query.get(course_id)
        if course:
            course.enrolled_count += 1
        db.session.commit()
        
        flash("Enrolled successfully!", "success")
    
    return redirect(url_for('student_courses'))

# Route for unenrolling from a course
@app.route('/unenroll/<int:course_id>')
@login_required
def unenroll(course_id):
    if current_user.role != 'student':
        flash("Access denied: Only students can unenroll from courses.", "danger")
        return redirect(url_for('home'))
    
    # Find the enrollment and delete it
    enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first()
    if enrollment:
        # Decrement the enrolled_count for the course
        course = Course.query.get(course_id)
        if course and course.enrolled_count > 0:
            course.enrolled_count -= 1

        db.session.delete(enrollment)
        db.session.commit()
        flash("Unenrolled successfully!", "success")
    else:
        flash("You are not enrolled in this course.", "info")
    
    return redirect(url_for('student_courses'))

# Route to log out the user
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.", "success")
    return redirect(url_for('login'))

# Function to create tables
def create_tables():
    with app.app_context():
        db.create_all()

# Run the application
if __name__ == '__main__':
    create_tables()  # Call to create tables before starting the app
    app.run(debug=True)
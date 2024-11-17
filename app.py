from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///enrollment.db'
app.config['SECRET_KEY'] = 'your_secret_key'

# Database and Login Manager initialization
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Admin interface setup
admin = Admin(app)

# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)  # Plain-text password
    role = db.Column(db.String(50))

    def check_password(self, password):
        return self.password == password  # Simple comparison

# Course model
class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(10), unique=True, nullable=False)
    course_name = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    teacher = db.Column(db.String(100), nullable=True)
    time = db.Column(db.String(50), nullable=True)
    enrolled_count = db.Column(db.Integer, default=0)

# Enrollment model
class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    grade = db.Column(db.String(2))

# Add models to the admin interface
admin.add_view(ModelView(User, db.session))
admin.add_view(ModelView(Course, db.session))
admin.add_view(ModelView(Enrollment, db.session))

# User loader callback for login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Student Enrollment System</title>
        <link rel="stylesheet" href="/static/styles.css">
    </head>
    <body>
        <div class="welcome-box">
            <h1>Welcome to the Student Enrollment Web App</h1>
            <p>Please log in to access your courses.</p>
            <div class="button-container">
                <a href="/login" class="login-button student-button">Student Login</a>
                <a href="/teacher_login" class="login-button teacher-button">Teacher Login</a>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.password == password:
            login_user(user)
            session['user_id'] = user.id  # Store user id in session

            if user.role == 'student':
                return redirect(url_for('student_courses'))  # Redirect to student courses
            elif user.role == 'teacher':
                return redirect(url_for('teacher_dashboard'))  # Redirect to teacher dashboard
            else:
                flash('Invalid user role', 'danger')
                return redirect(url_for('login'))
        else:
            flash('Invalid credentials', 'danger')
    
    return render_template('login.html')

@app.route('/student/courses')
@login_required
def student_courses():
    if current_user.role != 'student':
        flash("Access denied: Only students can view this page.", "danger")
        return redirect(url_for('login'))  # Redirect to login if not a student

    courses = Course.query.all()
    enrolled_course_ids = [enrollment.course_id for enrollment in Enrollment.query.filter_by(user_id=current_user.id).all()]
    return render_template('student_courses.html', courses=courses, enrolled_course_ids=enrolled_course_ids)

@app.route('/student/my_courses')
@login_required
def my_courses():
    if current_user.role != 'student':
        flash("Access denied: Only students can view this page.", "danger")
        return redirect(url_for('login'))

    enrollments = Enrollment.query.filter_by(user_id=current_user.id).all()
    enrolled_courses = [Course.query.get(enrollment.course_id) for enrollment in enrollments]
    return render_template('my_courses.html', courses=enrolled_courses)

@app.route('/enroll/<int:course_id>')
@login_required
def enroll(course_id):
    if current_user.role != 'student':
        flash("Access denied: Only students can enroll in courses.", "danger")
        return redirect(url_for('login'))

    existing_enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first()
    if existing_enrollment:
        flash("You are already enrolled in this course.", "info")
    else:
        new_enrollment = Enrollment(user_id=current_user.id, course_id=course_id)
        db.session.add(new_enrollment)

        course = Course.query.get(course_id)
        if course:
            course.enrolled_count += 1
        db.session.commit()
        
        flash("Enrolled successfully!", "success")
    
    return redirect(url_for('student_courses'))

@app.route('/unenroll/<int:course_id>')
@login_required
def unenroll(course_id):
    if current_user.role != 'student':
        flash("Access denied: Only students can unenroll from courses.", "danger")
        return redirect(url_for('login'))

    enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first()
    if enrollment:
        course = Course.query.get(course_id)
        if course and course.enrolled_count > 0:
            course.enrolled_count -= 1

        db.session.delete(enrollment)
        db.session.commit()
        flash("Unenrolled successfully!", "success")
    else:
        flash("You are not enrolled in this course.", "info")
    
    return redirect(url_for('student_courses'))

@app.route('/student_logout')
@login_required
def student_logout():
    logout_user()  # Log the student out
    session.pop('user_id', None)  # Clear session
    return redirect(url_for('login'))  # Redirect to login page

@app.route('/teacher_login', methods=['GET', 'POST'])
def teacher_login():
    if 'user_id' in session:
        return redirect(url_for('teacher_dashboard'))  # Redirect to dashboard if logged in
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        teacher = User.query.filter_by(username=username, role='teacher').first()
        if teacher and teacher.password == password:
            session['user_id'] = teacher.id
            login_user(teacher)
            return redirect(url_for('teacher_dashboard'))  # Redirect to dashboard
        else:
            flash("Invalid credentials", "danger")
    return render_template('teacher_login.html')

@app.route('/teacher_dashboard')
def teacher_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('teacher_login'))  # Redirect to login if not logged in
    
    return render_template('teacher_dashboard.html')

@app.route('/teacher_logout')
def teacher_logout():
    session.clear()  # Clear session to log out
    return redirect(url_for('teacher_login'))  # Redirect to login page

if __name__ == '__main__':
    app.run(debug=True)  # This starts the Flask development server with debug mode enabled
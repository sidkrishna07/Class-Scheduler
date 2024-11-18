from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_admin import Admin
from flask_admin.base import MenuLink
from flask_admin.contrib.sqla import ModelView
from flask_migrate import Migrate
from flask_admin.form import Select2Widget
from wtforms.fields import SelectField

app = Flask(__name__)


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///enrollment.db'
app.config['SECRET_KEY'] = 'your_secret_key'


db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150))
    password = db.Column(db.String(150))
    role = db.Column(db.String(50))  

    def check_password(self, password):
        return self.password == password


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(10))
    course_name = db.Column(db.String(100))
    capacity = db.Column(db.Integer)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    teacher = db.relationship('User', backref='teaching_courses', foreign_keys=[teacher_id])
    time = db.Column(db.String(50))
    enrolled_count = db.Column(db.Integer, default=0)


class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    grade = db.Column(db.String(5))

    # Define relationships
    user = db.relationship('User', backref='enrollments', lazy=True)
    course = db.relationship('Course', backref='enrollments', lazy=True)



admin = Admin(app, name='Admin Panel', template_mode='bootstrap4')
class EnrollmentView(ModelView):
    column_list = ('user.username', 'course.course_name', 'grade')

    
    column_searchable_list = ('user.username', 'course.course_name')

    
    column_sortable_list = ('user.username', 'course.course_name', 'grade')

    column_labels = {
        'user.username': 'Student',
        'course.course_name': 'Course',
        'grade': 'Grade'
    }


admin.add_view(ModelView(User, db.session, endpoint='admin_user'))
admin.add_view(ModelView(Course, db.session, endpoint='admin_course'))
admin.add_view(EnrollmentView(Enrollment, db.session, endpoint='admin_enrollment'))  
admin.add_link(MenuLink(name='Logout', endpoint='admin_logout'))


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
                <a href="/admin_login" class="login-button admin-button">Admin Login</a>
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

    # Query to fetch all courses along with the teacher's username
    courses = db.session.query(
        Course.id.label("id"),                 # Course ID
        Course.course_name.label("course_name"),  # Course Name
        User.username.label("teacher"),        # Teacher's Username
        Course.time.label("time"),             # Course Timing
        Course.enrolled_count.label("enrolled_count"),  # Students Enrolled
        Course.capacity.label("capacity")      # Maximum Students
    ).join(User, Course.teacher_id == User.id).all()

    # Fetch enrolled course IDs for the current user
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

@app.route('/add_course', methods=['POST'])
@login_required
def add_course():
    if current_user.role != 'teacher':
        flash("Access denied: Only teachers can add courses.", "danger")
        return redirect(url_for('teacher_dashboard'))

    course_name = request.form.get('course_name')
    course_code = request.form.get('course_code')
    time = request.form.get('time')
    capacity = request.form.get('capacity')

    new_course = Course(
        course_name=course_name,
        course_code=course_code,
        time=time,
        capacity=capacity,
        teacher_id=current_user.id
    )
    db.session.add(new_course)
    db.session.commit()

    flash("Course added successfully!", "success")
    return redirect(url_for('teacher_dashboard'))

@app.route('/enroll/<int:course_id>')
@login_required
def enroll(course_id):
    if current_user.role != 'student':
        flash("Access denied: Only students can enroll in courses.", "danger")
        return redirect(url_for('login'))

    course = Course.query.get(course_id)
    if not course:
        flash("Course not found.", "danger")
        return redirect(url_for('student_courses'))

   
    if course.enrolled_count >= course.capacity:
        flash("Cannot enroll: The course is full.", "danger")
        return redirect(url_for('student_courses'))

   
    existing_enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first()
    if existing_enrollment:
        flash("You are already enrolled in this course.", "info")
    else:
        
        new_enrollment = Enrollment(user_id=current_user.id, course_id=course_id)
        db.session.add(new_enrollment)

        
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
    return redirect(url_for('home'))  # Redirect to the main page

@app.route('/teacher_login', methods=['GET', 'POST'])
def teacher_login():
    if current_user.is_authenticated:
        return redirect(url_for('teacher_dashboard'))  # Redirect to dashboard if logged in
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        teacher = User.query.filter_by(username=username, role='teacher').first()

        if teacher and teacher.check_password(password):
            login_user(teacher)
            return redirect(url_for('teacher_dashboard'))  # Redirect to dashboard
        else:
            flash("Invalid credentials", "danger")

    return render_template('teacher_login.html')


@app.route('/assign_teacher', methods=['POST'])
@login_required
def assign_teacher():
    if current_user.role != 'teacher':
        flash("Access denied: Only teachers can assign courses.", "danger")
        return redirect(url_for('teacher_dashboard'))

    course_id = int(request.form.get('course_id'))
    teacher_id = int(request.form.get('teacher_id'))

    selected_course = Course.query.get(course_id)
    selected_teacher = User.query.get(teacher_id)

    if selected_course and selected_teacher:
        selected_course.teacher_id = selected_teacher.id  # Assign the teacher
        db.session.commit()
        flash(f"Teacher {selected_teacher.username} assigned to {selected_course.course_name} successfully.", "success")
    else:
        flash("Error: Course or Teacher not found.", "danger")

    return redirect(url_for('teacher_dashboard'))

@app.route('/teacher_dashboard', methods=['GET', 'POST'])
@login_required
def teacher_dashboard():
    if current_user.role != 'teacher':
        flash("Access denied: Only teachers can view this page.", "danger")
        return redirect(url_for('login'))

    # Fetch only the courses assigned to the logged-in teacher
    teacher_courses = Course.query.filter_by(teacher_id=current_user.id).all()

    if request.method == 'POST':
        # Handle course assignment functionality
        flash("Feature not available.", "danger")
        return redirect(url_for('teacher_dashboard'))  

    return render_template('teacher_dashboard.html', courses=teacher_courses)



@app.route('/teacher/course/<int:course_id>/students', methods=['GET', 'POST'])
@login_required
def view_students(course_id):
    if current_user.role != 'teacher':
        flash("Access denied: Only teachers can view this page.", "danger")
        return redirect(url_for('login'))
    course = Course.query.filter_by(id=course_id, teacher_id=current_user.id).first()
    if not course:
        flash("You do not have permission to view students for this course.", "danger")
        return redirect(url_for('teacher_dashboard'))

    if request.method == 'POST':
       
        for enrollment_id, grade in request.form.items():
            enrollment = Enrollment.query.get(int(enrollment_id))
            if enrollment and enrollment.course_id == course_id:
                enrollment.grade = grade
        db.session.commit()
        flash("Grades updated successfully!", "success")
        return redirect(url_for('view_students', course_id=course_id))

    enrollments = Enrollment.query.filter_by(course_id=course.id).all()
    students = [(User.query.get(enrollment.user_id), enrollment) for enrollment in enrollments]
    return render_template('students_enrolled.html', course=course, students=students)

@app.route('/teacher/course/<int:course_id>/grades')
@login_required
def view_grades(course_id):
    # Ensure the user is a teacher
    if current_user.role != 'teacher':
        flash("Access denied: Only teachers can view grades.", "danger")
        return redirect(url_for('login'))

    # Ensure the course exists and belongs to the teacher
    course = Course.query.filter_by(id=course_id, teacher_id=current_user.id).first()
    if not course:
        flash("You do not have permission to view grades for this course.", "danger")
        return redirect(url_for('teacher_dashboard'))

    # Retrieve enrolled students and their grades
    enrollments = Enrollment.query.filter_by(course_id=course.id).all()
    students_with_grades = [
        {
            "student": User.query.get(enrollment.user_id),
            "grade": enrollment.grade  # Assuming the `Enrollment` model has a `grade` column
        }
        for enrollment in enrollments
    ]

    # Render the grades page
    return render_template('grades.html', course=course, students_with_grades=students_with_grades)

@app.route('/teacher/students')
@login_required
def teacher_students():
    if current_user.role != 'teacher':
        flash("Access denied: Only teachers can view this page.", "danger")
        return redirect(url_for('login'))

  
    courses = Course.query.filter_by(teacher_id=current_user.id).all()

  
    students = []
    for course in courses:
        enrollments = Enrollment.query.filter_by(course_id=course.id).all()
        for enrollment in enrollments:
            student = User.query.get(enrollment.user_id)
            if student and student.role == 'student':
                students.append((student, course)) 

    return render_template('teacher_students.html', students=students)

@app.route('/teacher/course/<int:course_id>/edit_grades', methods=['GET', 'POST'])
@login_required
def edit_grades(course_id):
    if current_user.role != 'teacher':
        flash("Access denied: Only teachers can view this page.", "danger")
        return redirect(url_for('login'))

    course = Course.query.filter_by(id=course_id, teacher_id=current_user.id).first()
    if not course:
        flash("You do not have permission to edit grades for this course.", "danger")
        return redirect(url_for('teacher_dashboard'))

    if request.method == 'POST':
        for enrollment_id, grade in request.form.items():
            enrollment = Enrollment.query.get(int(enrollment_id))
            if enrollment:
                enrollment.grade = grade
        db.session.commit()
        flash("Grades updated successfully!", "success")
        return redirect(url_for('teacher_dashboard'))

    enrollments = Enrollment.query.filter_by(course_id=course.id).all()
    return render_template('edit_grades.html', course=course, enrollments=enrollments)


    return redirect(url_for('teacher_dashboard'))
@app.route('/teacher_logout')
@login_required
def teacher_logout():
    logout_user()  # Log the teacher out
    session.pop('user_id', None)  # Clear session
    return redirect(url_for('home'))  # Redirect to the main page

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated and current_user.role == 'admin':
        return redirect('/admin')  # Redirect to Flask-Admin dashboard if already logged in

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin_user = User.query.filter_by(username=username, role='admin').first()

        if admin_user and admin_user.check_password(password):
            login_user(admin_user)
            flash("Logged in as Admin successfully!", "success")
            return redirect('/admin')  # Redirect to Flask-Admin dashboard
        else:
            flash("Invalid credentials", "danger")

    return render_template('admin_login.html')

@app.route('/admin_logout')
@login_required
def admin_logout():
    if not current_user.is_authenticated or current_user.role != 'admin':
        flash("Access denied: Only admins can log out.", "danger")
        return redirect(url_for('login'))  # Redirect to login if not an admin

    logout_user()  # Logs out the current user
    flash("Logged out successfully.", "success")
    return redirect(url_for('home'))  # Redirect to the homepage

if __name__ == '__main__':
    app.run(host="127.0.0.1", port=5000, debug=True)



    
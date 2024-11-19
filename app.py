from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_admin import Admin
from flask_admin.base import MenuLink
from flask_admin.contrib.sqla import ModelView
from flask_migrate import Migrate
from wtforms.fields import SelectField

app = Flask(__name__)

# Configurations
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///enrollment.db'
app.config['SECRET_KEY'] = 'your_secret_key'

# Extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150))
    password = db.Column(db.String(150))
    role = db.Column(db.String(50))

    def check_password(self, password):
        return self.password == password  # Replace with hashing for production!

    def __str__(self):
        return self.username  # Ensures username displays in admin panels


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(10), )
    course_name = db.Column(db.String(100), )
    capacity = db.Column(db.Integer, )
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    teacher = db.relationship('User', backref='teaching_courses', foreign_keys=[teacher_id])
    time = db.Column(db.String(50))
    enrolled_count = db.Column(db.Integer, default=0)


class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    grade = db.Column(db.String(5))

    user = db.relationship('User', backref='enrollments')
    course = db.relationship('Course', backref='enrollments')


# Admin Panel
admin = Admin(app, name='Admin Panel', template_mode='bootstrap4')


class EnrollmentView(ModelView):
    # Display these columns in the admin list view
    column_list = ('user.username', 'course.course_name', 'grade')

    # Define custom column labels
    column_labels = {
        'user.username': 'Student',
        'course.course_name': 'Course',
        'grade': 'Grade',
    }

    # Make these columns searchable in the admin panel
    column_searchable_list = ('user.username', 'course.course_name')

    # Allow sorting by these columns
    column_sortable_list = ('user.username', 'course.course_name', 'grade')

    # Specify the fields that will be displayed in the edit form
    form_columns = ['user_id', 'course_id', 'grade']

    # Prefill the form with choices for user and course dropdowns
    def on_form_prefill(self, form, id):
        form.user_id.choices = [(u.id, u.username) for u in User.query.all()] or [('', 'No Users')]
        form.course_id.choices = [(c.id, c.course_name) for c in Course.query.all()] or [('', 'No Courses')]

    # Validate the form to make sure user_id and course_id are selected
    def on_model_change(self, form, model, is_created):
        if not model.user_id or not model.course_id:
            raise ValueError("Both User and Course must be selected.")
        return super().on_model_change(form, model, is_created)

    # Format the columns in the list view
    column_formatters = {
        'user.username': lambda v, c, m, p: f"{m.user.username}",  # Display student's username
        'course.course_name': lambda v, c, m, p: f"{m.course.course_name}",  # Display course name
        'grade': lambda v, c, m, p: f"{m.grade}"  # Display the grade
    }







admin.add_view(ModelView(User, db.session, endpoint='admin_user'))
admin.add_view(ModelView(Course, db.session, endpoint='admin_course'))
admin.add_view(EnrollmentView(Enrollment, db.session, endpoint='admin_enrollment'))
#admin.add_link(MenuLink(name='Logout', endpoint='admin_logout'))

# Login Manager
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def home():
    return render_template('home.html')  


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            session['user_id'] = user.id
            return redirect(url_for(f'{user.role}_dashboard'))  # Redirect based on role

        flash('Invalid credentials', 'danger')
    return render_template('login.html')


@app.route('/student_dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        flash("Access denied.", "danger")
        return redirect(url_for('login'))
    # Fetch courses and enrollments for student
    return render_template('student_dashboard.html')


@app.route('/teacher_dashboard')
@login_required
def teacher_dashboard():
    if current_user.role != 'teacher':
        flash("Access denied.", "danger")
        return redirect(url_for('login'))
    teacher_courses = Course.query.filter_by(teacher_id=current_user.id).all()
    return render_template('teacher_dashboard.html', courses=teacher_courses)


@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin_user = User.query.filter_by(username=username, role='admin').first()

        if admin_user and admin_user.check_password(password):
            login_user(admin_user)
            return redirect('/admin')  # Redirect to Flask-Admin

        flash("Invalid credentials", "danger")
    return render_template('admin_login.html')


@app.route('/admin_logout')
@login_required
def admin_logout():
    if current_user.role == 'admin':
        logout_user()
        flash("Logged out successfully.", "success")
        return redirect(url_for('home'))
    flash("Access denied.", "danger")
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)

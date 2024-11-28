
from flask_login import LoginManager, login_user, current_user, logout_user, login_required, UserMixin
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
import MySQLdb.cursors

app = Flask(__name__)
app.secret_key = 'secret'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'flask_crud4'

mysql = MySQL(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

# Mock User class (replace with your actual User model)
class User(UserMixin):
    def __init__(self, user_id, username, name):
        self.id = user_id
        self.username = username
        self.name = name

# User loader function (fetch user from database)
@login_manager.user_loader
def load_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    user_data = cur.fetchone()
    cur.close()
    if user_data:
        return User(user_data[0], user_data[3], user_data[1])  # Access elements by index
    return None



# Login route
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cur = mysql.connection.cursor()
        cur.execute('SELECT * FROM users WHERE username = %s AND password = %s', (username, password,))
        account = cur.fetchone()
        cur.close()
        
        if account:
            session['loggedin'] = True
            session['user_id'] = account[0]  
            session['username'] = account[3]
            session['name'] = account[1]
            user_id = account[0]  
            username = account[3]
            name = account[1]
            user = User(user_id, username, name)
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('Index'))  # Redirect to index page after successful login
        else:
            flash('Invalid username or password', 'error')

    # If it's a GET request or login failed, render the login form
    return render_template('login.html')

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully', 'info')
    return redirect(url_for('login'))

# Example protected route
@app.route('/protected')
@login_required
def protected_route():
    return "This is a protected route. You can only see this if you're logged in."


# Signup Page
@app.route('/signup')
def signup():
    return render_template('signup.html')

# Register Route
@app.route('/register', methods=['POST'])
def register():
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']
    
    try:
        cursor = mysql.connection.cursor()
        cursor.execute('INSERT INTO users (first_name, last_name, username, email, password) VALUES (%s, %s, %s, %s, %s)',
                       (first_name, last_name, username, email, password,))
        mysql.connection.commit()
        cursor.close()
        
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))
    except mysql.connection.IntegrityError as e:
        flash('Error: Email address already exists.', 'danger')
        return redirect(url_for('signup'))













# settings route to handle both GET and POST requests
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    # Check if user is logged in
    if 'loggedin' not in session:
        flash('Please log in to access settings.', 'error')
        return redirect(url_for('login'))
    
    # Fetch user details from the database
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT first_name, last_name, username FROM users WHERE user_id = %s', (session['user_id'],))
    user = cursor.fetchone()
    
    if request.method == 'POST':
        # Extract data from the form
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Validate password match
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('settings.html', user=user)

        # Update user information in the database
        try:
            cursor.execute('''
                UPDATE users
                SET first_name = %s, last_name = %s, username = %s, password = %s
                WHERE user_id = %s
            ''', (first_name, last_name, username, password, session['user_id']))
            mysql.connection.commit()
            flash('Settings updated successfully', 'success')
        except MySQLdb.IntegrityError:
            flash('Username already exists. Choose another one.', 'error')

        # Fetch updated user data after the update
        cursor.execute('SELECT first_name, last_name, username FROM users WHERE user_id = %s', (session['user_id'],))
        user = cursor.fetchone()

    cursor.close()
    return render_template('settings.html', user=user)








@app.route('/home')
@login_required
def Index():
    # Ensure user is authenticated and retrieve user information from session or wherever it's stored
    if 'user_id' in session and 'username' in session and 'name' in session:
        user_id = session['user_id']
        username = session['username']  
        name = session['name']

        cur = mysql.connection.cursor()
        # Fetch patient list with doctor names
        cur.execute("""
            SELECT p.id, p.name, p.email, p.phone, p.address, p.weight, p.height, p.blood_type, d.name as doctor_name
            FROM patients p
            LEFT JOIN doctors d ON p.doctor_assigned = d.doctor_id
        """)
        patients = cur.fetchall()
        cur.close()

        # Pass patient data and user information to template
        return render_template('Index.html', patients=patients, current_user={'name': name, 'id': user_id, 'username': username})
    else:
        # Handle case where user is not authenticated (redirect to login, etc.)
        return redirect(url_for('login'))


# Route to render the add patient form
@app.route('/add_patient')
@login_required
def add_patient():
    cur = mysql.connection.cursor()
    cur.execute("SELECT doctor_id, name FROM doctors")
    doctors = cur.fetchall()
    cur.close()
    return render_template('add_patient.html', doctors=doctors)

# add patient
@app.route('/insert', methods=['POST'])
@login_required
def insert():
    if request.method == "POST":
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        address = request.form['address']
        weight = request.form['weight']
        height = request.form['height']
        blood_type = request.form['blood_type']
        doctor_assigned = request.form['doctor_assigned']

        # Handle the case where no doctor is selected
        if doctor_assigned == '':
            doctor_assigned = None

        cur = mysql.connection.cursor()
        try:
            cur.execute("""
                INSERT INTO patients (name, email, phone, address, weight, height, blood_type, doctor_assigned)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (name, email, phone, address, weight, height, blood_type, doctor_assigned))
            mysql.connection.commit()
            flash("Data Inserted Successfully")
        except Exception as e:
            mysql.connection.rollback()
            flash(f"An error occurred: {str(e)}")
        finally:
            cur.close()

        return redirect(url_for('Index'))



# delete patient
@app.route('/delete/<string:id_data>', methods=['GET'])
@login_required
def delete(id_data):
    cur = mysql.connection.cursor()

    # Check if patient has associated records
    cur.execute("SELECT * FROM records WHERE patient_id=%s", (id_data,))
    records = cur.fetchall()

    if records:
        flash("Cannot delete patient because records exist.")
        return redirect(url_for('Index'))

    # Check if patient has associated admission details
    cur.execute("SELECT * FROM admission_details WHERE patient_id=%s", (id_data,))
    admissions = cur.fetchall()

    if admissions:
        flash("Cannot delete patient because admission details exist.")
        return redirect(url_for('Index'))

    # If no records or admission details exist, proceed with deletion
    cur.execute("DELETE FROM patients WHERE id=%s", (id_data,))
    mysql.connection.commit()
    flash("Patient Deleted Successfully")

    cur.close()

    return redirect(url_for('Index'))




# update button patient
@app.route('/update_patient', methods=['POST'])
@login_required
def update_patient():
    if request.method == 'POST':
        id_data = request.form['id']
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        address = request.form['address']
        weight = request.form['weight']
        height = request.form['height']
        blood_type = request.form['blood_type']
        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE patients
            SET name=%s, email=%s, phone=%s, address=%s, weight=%s, height=%s, blood_type=%s
            WHERE id=%s
        """, (name, email, phone, address, weight, height, blood_type, id_data))
        mysql.connection.commit()
        flash("Data Updated Successfully")
        return redirect(url_for('Index'))




# edit patient
@app.route('/edit_patient/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def edit_patient(patient_id):
    cur = mysql.connection.cursor()
    
    if request.method == 'GET':
        try:
            # Fetch patient data
            cur.execute("SELECT * FROM patients WHERE id=%s", (patient_id,))
            patient = cur.fetchone()
            if not patient:
                flash("Patient not found")
                return redirect(url_for('Index'))
            
            # Fetch doctors data
            cur.execute("SELECT doctor_id, name FROM doctors")
            doctors = cur.fetchall()
            
            return render_template('edit_patient.html', patient=patient, doctors=doctors)
        except Exception as e:
            flash(f"An error occurred while fetching the patient data: {e}")
            return redirect(url_for('Index'))
        finally:
            cur.close()
    
    elif request.method == 'POST':
        try:
            id_data = request.form['id']
            name = request.form['name']
            email = request.form['email']
            phone = request.form['phone']
            address = request.form['address']
            weight = request.form['weight']
            height = request.form['height']
            blood_type = request.form['blood_type']
            doctor_assigned = request.form['doctor_assigned']

            # Check if doctor_assigned exists in doctors table
            cur.execute("SELECT * FROM doctors WHERE doctor_id=%s", (doctor_assigned,))
            doctor = cur.fetchone()
            if not doctor:
                flash("Doctor does not exist. Please select a valid doctor.")
                return redirect(url_for('edit_patient', patient_id=patient_id))

            cur.execute(""" 
                UPDATE patients
                SET name=%s, email=%s, phone=%s, address=%s, weight=%s, height=%s, blood_type=%s, doctor_assigned=%s
                WHERE id=%s
            """, (name, email, phone, address, weight, height, blood_type, doctor_assigned, id_data))
            mysql.connection.commit()
            flash("Data Updated Successfully")
        except Exception as e:
            flash(f"An error occurred while updating the patient data: {e}")
        finally:
            cur.close()
        
        return redirect(url_for('Index'))





# view patient
@app.route('/view_patient/<int:patient_id>')
@login_required
def view_patient(patient_id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Fetch patient details including the doctor's name
    cur.execute("""
        SELECT p.*, d.name as doctor_name 
        FROM patients p
        LEFT JOIN doctors d ON p.doctor_assigned = d.doctor_id
        WHERE p.id = %s
    """, (patient_id,))
    patient = cur.fetchone()
    
    if not patient:
        flash("Patient not found")
        return redirect(url_for('Index'))

    # Fetch records
    cur.execute("SELECT * FROM records WHERE patient_id = %s", (patient_id,))
    records = cur.fetchall()
    
    # Fetch admission details including the doctor's name
    cur.execute("""
        SELECT a.*, d.name as doctor_name 
        FROM admission_details a
        LEFT JOIN doctors d ON a.doctor_assigned = d.doctor_id
        WHERE a.patient_id = %s
    """, (patient_id,))
    admissions = cur.fetchall()

    cur.close()

    return render_template('view_patient.html', patient=patient, records=records, admissions=admissions)












# PATIENT RECORDS
# add patient record
@app.route('/add_record/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def processrecord(patient_id):
    if request.method == 'POST':
        diagnosis = request.form['diagnosis']
        treatment_plan = request.form['treatment_plan']
        date_of_visit = request.form['date_of_visit']
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO records (patient_id, diagnosis, treatment_plan, date_of_visit) VALUES (%s, %s, %s, %s)",
                    (patient_id, diagnosis, treatment_plan, date_of_visit))
        mysql.connection.commit()
        flash("Record Added Successfully")
        return redirect(url_for('view_patient', patient_id=patient_id))
    return render_template('add_record.html', patient_id=patient_id)


# edit patient record
@app.route('/edit_record/<int:record_id>', methods=['GET', 'POST'])
@login_required
def edit_record(record_id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if request.method == 'POST':
        diagnosis = request.form['diagnosis']
        treatment_plan = request.form['treatment_plan']
        date_of_visit = request.form['date_of_visit']
        cur.execute("""
            UPDATE records
            SET diagnosis=%s, treatment_plan=%s, date_of_visit=%s
            WHERE record_id=%s
        """, (diagnosis, treatment_plan, date_of_visit, record_id))
        mysql.connection.commit()
        flash("Record Updated Successfully")
        return redirect(url_for('view_patient', patient_id=request.form['patient_id']))
    else:
        cur.execute("SELECT * FROM records WHERE record_id = %s", (record_id,))
        record = cur.fetchone()
        return render_template('edit_record.html', record=record)


# delete patient record
@app.route('/delete_record/<int:record_id>', methods=['GET'])
@login_required
def delete_record(record_id):
    cur = mysql.connection.cursor()

    # Fetch patient_id before deleting the record
    cur.execute("SELECT patient_id FROM records WHERE record_id = %s", (record_id,))
    result = cur.fetchone()

    if not result:
        flash("Error: Record not found")
        cur.close()
        return redirect(url_for('Index'))  # Redirect to index if record not found

    patient_id = result[0]  # Access the first element of the tuple

    # Delete the record
    cur.execute("DELETE FROM records WHERE record_id=%s", (record_id,))
    mysql.connection.commit()
    flash("Record Deleted Successfully")

    cur.close()

    # Redirect to view_patient page with the correct patient_id
    return redirect(url_for('view_patient', patient_id=patient_id))









# ADD ADMISSION DETAILS
# add admission details
@app.route('/add_admission/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def add_admission(patient_id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    if request.method == 'POST':
        admission_date = request.form['admission_date']
        discharge_date = request.form['discharge_date']
        room_number = request.form['room_number']
        doctor_assigned = request.form['doctor_assigned']
        
        cur.execute("""
            INSERT INTO admission_details (patient_id, admission_date, discharge_date, room_number, doctor_assigned)
            VALUES (%s, %s, %s, %s, %s)
        """, (patient_id, admission_date, discharge_date, room_number, doctor_assigned))
        mysql.connection.commit()
        flash("Admission Details Added Successfully")
        return redirect(url_for('view_patient', patient_id=patient_id))

    # Fetch list of doctors for the dropdown
    cur.execute("SELECT doctor_id, name FROM doctors")
    doctors = cur.fetchall()
    cur.close()
    
    return render_template('add_admission.html', patient_id=patient_id, doctors=doctors)



@app.route('/edit_admission/<int:admission_id>', methods=['GET', 'POST'])
@login_required
def edit_admission(admission_id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        # Retrieve data from the form
        admission_date = request.form['admission_date']
        discharge_date = request.form['discharge_date']
        room_number = request.form['room_number']
        doctor_assigned = request.form['doctor_assigned']  # Ensure doctor_assigned is fetched from form
        patient_id = request.form['patient_id']  # Ensure patient_id is fetched from form

        # Update the admission details in the database
        cur.execute("""
            UPDATE admission_details
            SET admission_date=%s, discharge_date=%s, room_number=%s, doctor_assigned=%s
            WHERE admission_id=%s
        """, (admission_date, discharge_date, room_number, doctor_assigned, admission_id))
        mysql.connection.commit()

        flash("Admission Details Updated Successfully", "success")

        # Redirect to view_patient page after successful update
        return redirect(url_for('view_patient', patient_id=patient_id))
    else:
        # Fetch the admission details for editing
        cur.execute("SELECT * FROM admission_details WHERE admission_id = %s", (admission_id,))
        admission = cur.fetchone()

        # Ensure admission data is fetched successfully
        if not admission:
            flash("Error: Admission details not found", "error")
            return redirect(url_for('Index'))  # Redirect to index if admission details not found

        # Fetch all doctors for the dropdown
        cur.execute("SELECT doctor_id, name FROM doctors")
        doctors = cur.fetchall()

        patient_id = admission['patient_id']  # Fetch patient_id from admission details

        cur.close()

        # Pass admission, doctors, and patient_id to the template context for rendering
        return render_template('edit_admission.html', admission=admission, doctors=doctors, patient_id=patient_id)




# delete admission details
@app.route('/delete_admission/<int:admission_id>/<int:patient_id>', methods=['GET'])
@login_required
def delete_admission(admission_id, patient_id):
    cur = mysql.connection.cursor()

    # Delete the admission detail
    cur.execute("DELETE FROM admission_details WHERE admission_id=%s", (admission_id,))
    mysql.connection.commit()
    flash("Admission Details Deleted Successfully")

    cur.close()

    return redirect(url_for('view_patient', patient_id=patient_id))






# View doctors
@app.route('/view_doctors')
@login_required
def view_doctors():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM doctors")
    doctors = cur.fetchall()
    cur.close()
    return render_template('view_doctors.html', doctors=doctors)

# Add doctor
@app.route('/add_doctor', methods=['GET', 'POST'])
@login_required
def insert_doctor():
    if request.method == "POST":
        name = request.form['name']
        specialization = request.form['specialization']
        
        # Insert data into the database
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO doctors (name, specialization) VALUES (%s, %s)", (name, specialization))
        mysql.connection.commit()
        flash("Doctor Inserted Successfully")
        cur.close()
        
        # Redirect to view_doctors after adding doctor
        return redirect(url_for('view_doctors'))

    return render_template('add_doctor.html')

# Delete doctor
@app.route('/delete_doctor/<int:doctor_id>', methods=['GET'])
@login_required
def delete_doctor(doctor_id):
    cur = mysql.connection.cursor()

    # Check if the doctor is assigned to any patients
    cur.execute("SELECT * FROM patients WHERE doctor_assigned=%s", (doctor_id,))
    patients = cur.fetchall()

    if patients:
        flash("Cannot delete doctor because they are assigned to patients.")
        return redirect(url_for('view_doctors'))

    # Proceed with deleting the doctor if no patients are assigned
    cur.execute("DELETE FROM doctors WHERE doctor_id=%s", (doctor_id,))
    mysql.connection.commit()
    flash("Doctor Deleted Successfully")

    cur.close()

    return redirect(url_for('view_doctors'))





# update doctor info
@app.route('/update_doctor', methods=['POST'])
@login_required
def update_doctor():
    if request.method == 'POST':
        doctor_id = request.form['doctor_id']
        name = request.form['name']
        specialization = request.form['specialization']

        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE doctors
            SET name=%s, specialization=%s
            WHERE doctor_id=%s
        """, (name, specialization, doctor_id))
        mysql.connection.commit()
        flash("Doctor Updated Successfully")
        cur.close()

        return redirect(url_for('view_doctors'))




# edit doctor
@app.route('/edit_doctor/<int:doctor_id>', methods=['GET', 'POST'])
@login_required
def edit_doctor(doctor_id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'GET':
        cur.execute("SELECT * FROM doctors WHERE doctor_id=%s", (doctor_id,))
        doctor = cur.fetchone()
        cur.close()

        if doctor:
            return render_template('edit_doctor.html', doctor=doctor)
        else:
            flash("Doctor not found")
            return redirect(url_for('view_doctors'))

    elif request.method == 'POST':
        name = request.form['name']
        specialization = request.form['specialization']

        cur.execute("""
            UPDATE doctors
            SET name=%s, specialization=%s
            WHERE doctor_id=%s
        """, (name, specialization, doctor_id))
        mysql.connection.commit()
        cur.close()

        flash("Doctor Updated Successfully")
        return redirect(url_for('view_doctors'))










if __name__ == "__main__":
    app.run(debug=True)

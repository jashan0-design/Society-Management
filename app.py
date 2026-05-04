import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import random
import string
from datetime import datetime
from urllib.parse import urlparse

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', "elite_society_secret_key_2024")

db_uri = os.environ.get('DATABASE_URL', 'sqlite:///society.db')
if db_uri.startswith("postgres://"):
    db_uri = "postgresql://"+db_uri[10:]
app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class LoginRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), nullable=False)
    user_type = db.Column(db.String(50), nullable=False)
    login_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    logout_time = db.Column(db.DateTime, nullable=True)

class Resident(db.Model):
    id = db.Column(db.String(10), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    building = db.Column(db.String(100), nullable=False)
    flat = db.Column(db.String(20), nullable=False)
    contact = db.Column(db.String(20))

class Building(db.Model):
    name = db.Column(db.String(100), primary_key=True)
    floors = db.Column(db.Integer)
    flats = db.Column(db.Integer)
    occupancy = db.Column(db.String(10))
    description = db.Column(db.Text)
    residents_count = db.Column(db.Integer, default=0)
    amenities = db.Column(db.Text)  # JSON string
    manager = db.Column(db.String(200))

class Wing(db.Model):
    name = db.Column(db.String(100), primary_key=True)
    slug = db.Column(db.String(100))
    description = db.Column(db.Text)
    units = db.Column(db.Integer)

class Notice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    date = db.Column(db.String(20))
    content = db.Column(db.Text, nullable=False)

class Bill(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    type = db.Column(db.String(100))
    amount = db.Column(db.String(20))
    due_date = db.Column(db.String(20))
    status = db.Column(db.String(20), default='Pending')
    details = db.Column(db.Text)
    target = db.Column(db.String(100))
    paid_date = db.Column(db.String(20))
    payment_reference = db.Column(db.String(50))
    payment_details = db.Column(db.Text)  # JSON

class Complaint(db.Model):
    id = db.Column(db.String(20), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category = db.Column(db.String(50), default='General')
    priority = db.Column(db.String(20), default='Medium')
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Filed')
    date = db.Column(db.String(30))
    user = db.relationship('User', backref='complaints')

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Global lists will be replaced by queries

# Helper functions
def generate_complaint_id():
    return 'SOC-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def seed_data():
    """Seed sample data if not exists"""
    # Create initial admin user if not exists
    if not User.query.filter_by(username='jashan').first():
        admin_user = User(username='jashan', email='admin@society.com')
        admin_user.set_password('1234')
        admin_user.is_admin = True
        db.session.add(admin_user)
    
    # Create demo resident user
    if not User.query.filter_by(username='demo').first():
        demo_user = User(username='demo', email='demo@society.com')
        demo_user.set_password('1234')
        db.session.add(demo_user)
    
    if Resident.query.first() is None:
        residents_data = [
            Resident(id="R001", name="Aman Sharma", building="Building A", flat="A-101", contact="+91-98765 43201"),
            Resident(id="R002", name="Neha Verma", building="Building B", flat="B-203", contact="+91-98765 43202"),
            Resident(id="R003", name="Rahul Mehta", building="Building C", flat="C-304", contact="+91-98765 43203"),
            Resident(id="R004", name="Priya Singh", building="Building D", flat="D-107", contact="+91-98765 43204")
        ]
        db.session.bulk_save_objects(residents_data)
        
        buildings_data = [
            Building(name="Building A", floors=4, flats=24, occupancy="96%", description="Premier tower with river-facing apartments.", residents_count=92, amenities='["Rooftop Pool", "Gym", "Garden"]', manager="Mr. Raj Patel (+91-98765 43210)"),
            Building(name="Building B", floors=5, flats=30, occupancy="88%", description="Modern block with rooftop lounge and kids area.", residents_count=89, amenities='["Kids Play Area", "Lounge", "Laundry"]', manager="Ms. Priya Singh (+91-98765 43211)"),
            Building(name="Building C", floors=4, flats=20, occupancy="100%", description="Cozy building with quiet garden access.", residents_count=80, amenities='["Garden", "Senior Lounge", "Library"]', manager="Mr. Anil Kumar (+91-98765 43212)"),
            Building(name="Building D", floors=3, flats=18, occupancy="94%", description="Smart residential tower with premium security.", residents_count=17, amenities='["Security Booth", "EV Charging", "Smart Locks"]', manager="Mr. Vikram Joshi (+91-98765 43213)")
        ]
        db.session.bulk_save_objects(buildings_data)
        
        wings_data = [
            Wing(name="Wing A", slug="wing-a", description="Lake-facing apartments with premium amenities.", units=32),
            Wing(name="Wing B", slug="wing-b", description="Family-friendly block with dedicated play area.", units=28),
            Wing(name="Wing C", slug="wing-c", description="Tower with smart security and rooftop garden.", units=30),
            Wing(name="Wing D", slug="wing-d", description="Quiet residential wing with easy parking access.", units=26)
        ]
        db.session.bulk_save_objects(wings_data)
        
        bills_data = [
            Bill(id="water", type="Water Bill", amount="₹2,450", due_date="15 May 2024", status="Pending", details="25 units @ ₹98/unit", target="All Residents"),
            Bill(id="electricity", type="Electricity Bill", amount="₹3,200", due_date="20 May 2024", status="Pending", details="320 units @ ₹10/unit", target="All Residents")
        ]
        db.session.bulk_save_objects(bills_data)
        
        notices_data = [
            Notice(title="Maintenance Work", date="10 May 2024", content="Building maintenance scheduled for next weekend."),
            Notice(title="Security Update", date="5 May 2024", content="New security protocols implemented."),
            Notice(title="Community Festival", date="15 May 2024", content="Annual fest with food, games, and cultural performances."),
            Notice(title="Water Conservation Drive", date="20 May 2024", content="Join the society-wide water saving campaign this week.")
        ]
        db.session.bulk_save_objects(notices_data)
        
        db.session.commit()
        print("Sample data seeded!")

# Routes
@app.route('/')
def index():
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user_type = request.form.get('user_type')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['logged_in'] = True
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_type'] = 'admin' if user.is_admin else 'resident'
            record = LoginRecord(username=username, user_type=session['user_type'])
            db.session.add(record)
            db.session.commit()
            session['login_record_id'] = record.id
            flash(f'{session["user_type"].title()} login successful!', 'success')
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials. Try demo/1234 (resident) or jashan/1234 (admin).', 'error')
    return render_template('login.html')

@app.route('/admin_login')
def admin_login():
    return render_template('admin_login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    if session.get('user_type') == 'admin':
        return redirect(url_for('admin_dashboard'))
    statistics = {
        'total_residents': Resident.query.count(),
        'active_notices': Notice.query.count(),
        'pending_complaints': Complaint.query.filter(Complaint.status != 'Resolved').count(),
        'upcoming_events': 3
    }
    wings = Wing.query.all()
    return render_template('dashboard.html', wings=wings, statistics=statistics)

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'logged_in' not in session or session.get('user_type') != 'admin':
        return redirect(url_for('login'))
    statistics = {
        'total_residents': Resident.query.count(),
        'pending_complaints': Complaint.query.filter(Complaint.status != 'Resolved').count(),
        'pending_bills': Bill.query.filter(Bill.status != 'Paid').count(),
        'total_notices': Notice.query.count(),
        'total_buildings': Building.query.count(),
        'total_residence_units': sum(b.flats or 0 for b in Building.query.all())
    }
    return render_template('admin_dashboard.html', statistics=statistics)

@app.route('/admin_login_history')
def admin_login_history():
    if 'logged_in' not in session or session.get('user_type') != 'admin':
        return redirect(url_for('login'))
    records = LoginRecord.query.order_by(LoginRecord.login_time.desc()).all()
    return render_template('admin_login_history.html', records=records)

@app.route('/admin_bills', methods=['GET', 'POST'])
def admin_bills():
    if 'logged_in' not in session or session.get('user_type') != 'admin':
        return redirect(url_for('login'))
    bills_list = Bill.query.all()
    residents_list = Resident.query.all()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            bill_id = request.form.get('id')
            bill_type = request.form.get('type')
            amount = request.form.get('amount')
            due_date = request.form.get('due_date')
            details = request.form.get('details')
            target = request.form.get('target', 'All Residents')
            new_bill = Bill(id=bill_id, type=bill_type, amount=amount, due_date=due_date, status='Pending', details=details, target=target)
            db.session.add(new_bill)
            db.session.commit()
            flash('New bill created and sent to residents.', 'success')
        elif action == 'delete':
            bill_id = request.form.get('id')
            bill = Bill.query.get(bill_id)
            if bill:
                db.session.delete(bill)
                db.session.commit()
            flash('Bill removed successfully.', 'success')
        return redirect(url_for('admin_bills'))
    return render_template('admin_bills.html', bills=bills_list, residents=residents_list)

@app.route('/admin_buildings', methods=['GET', 'POST'])
def admin_buildings():
    if 'logged_in' not in session or session.get('user_type') != 'admin':
        return redirect(url_for('login'))
    buildings_list = Building.query.all()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            name = request.form.get('name')
            floors = int(request.form.get('floors') or 0)
            flats = int(request.form.get('flats') or 0)
            description = request.form.get('description')
            manager = request.form.get('manager')
            new_building = Building(name=name, floors=floors, flats=flats, occupancy='0%', description=description, manager=manager)
            db.session.add(new_building)
            db.session.commit()
            flash('Building added successfully.', 'success')
        elif action == 'delete':
            name = request.form.get('name')
            building = Building.query.get(name)
            if building:
                db.session.delete(building)
                db.session.commit()
            flash('Building removed successfully.', 'success')
        elif action == 'update_floors':
            name = request.form.get('name')
            new_floors = int(request.form.get('floors') or 0)
            building = Building.query.get(name)
            if building:
                building.floors = new_floors
                db.session.commit()
            flash('Building floor count updated.', 'success')
        return redirect(url_for('admin_buildings'))
    return render_template('admin_buildings.html', buildings=buildings_list)

@app.route('/admin_residents', methods=['GET', 'POST'])
def admin_residents():
    if 'logged_in' not in session or session.get('user_type') != 'admin':
        return redirect(url_for('login'))
    residents_list = Resident.query.all()
    buildings_list = Building.query.all()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            resident_id = 'R' + ''.join(random.choices(string.digits, k=3))
            name = request.form.get('name')
            building_name = request.form.get('building')
            flat = request.form.get('flat')
            contact = request.form.get('contact')
            new_resident = Resident(id=resident_id, name=name, building=building_name, flat=flat, contact=contact)
            db.session.add(new_resident)
            db.session.commit()
            flash('Resident added successfully.', 'success')
        elif action == 'delete':
            resident_id = request.form.get('id')
            resident = Resident.query.get(resident_id)
            if resident:
                db.session.delete(resident)
                db.session.commit()
            flash('Resident removed successfully.', 'success')
        return redirect(url_for('admin_residents'))
    return render_template('admin_residents.html', residents=residents_list, buildings=buildings_list)

@app.route('/admin_complaints', methods=['GET', 'POST'])
def admin_complaints():
    if 'logged_in' not in session or session.get('user_type') != 'admin':
        return redirect(url_for('login'))
    complaints_list = Complaint.query.all()
    if request.method == 'POST':
        action = request.form.get('action')
        complaint_id = request.form.get('id')
        if action == 'resolve':
            complaint = Complaint.query.get(complaint_id)
            if complaint:
                complaint.status = 'Resolved'
                db.session.commit()
            flash('Complaint marked resolved.', 'success')
        elif action == 'delete':
            complaint = Complaint.query.get(complaint_id)
            if complaint:
                db.session.delete(complaint)
                db.session.commit()
            flash('Complaint deleted.', 'success')
        return redirect(url_for('admin_complaints'))
    return render_template('admin_complaints.html', complaints=complaints_list)

@app.route('/pay_bill/<bill_id>', methods=['GET', 'POST'])
def pay_bill(bill_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    bill = Bill.query.get(bill_id)
    if not bill:
        flash('Bill not found.', 'error')
        return redirect(url_for('bills_page'))

    if request.method == 'POST':
        account_number = request.form.get('account_number')
        ifsc_code = request.form.get('ifsc_code')
        account_holder = request.form.get('account_holder')
        amount_paid = request.form.get('amount')
        payment_mode = request.form.get('payment_mode')

        # Mark bill paid and store payment metadata
        bill.status = 'Paid'
        bill.paid_date = datetime.now().strftime('%d %B %Y')
        bill.payment_reference = 'TXN' + ''.join(random.choices(string.digits, k=8))
        bill.payment_details = str({
            'account_number': account_number,
            'ifsc_code': ifsc_code,
            'account_holder': account_holder,
            'amount': amount_paid,
            'payment_mode': payment_mode
        })
        db.session.commit()
        flash(f"{bill.type} payment completed successfully.", 'success')
        return redirect(url_for('bills_page'))

    return render_template('pay_bill.html', bill=bill)

@app.route('/action/<action_name>')
def action_page(action_name):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    action_map = {
        'edit_personal': 'Edit your personal profile details.',
        'edit_apartment': 'Update apartment details and visitor access rules.',
        'add_member': 'Add a new family member to your apartment.',
        'edit_contacts': 'Manage your emergency contact list.',
        'change_password': 'Change your login password securely.',
        'manage_2fa': 'Manage two-factor authentication preferences.',
        'view_notices': 'Browse all society notices in detail.',
        'subscribe_notices': 'Subscribe to newsletter and receive alerts by email.',
        'emergency_report': 'Report an urgent society issue to the support team.'
    }
    message = action_map.get(action_name, 'This action is available soon.')
    return render_template('action.html', action_name=action_name, message=message)

@app.route('/complaints', methods=['GET', 'POST'])
def complaints_page():
    if 'logged_in' not in session or 'user_id' not in session:
        return redirect(url_for('login'))

    ticket = None
    status_message = None
    my_complaints = []
    categories = ['General', 'Lift/Elevator', 'Water Supply', 'Electricity', 'Security', 'Cleaning', 'Parking', 'Maintenance', 'Other']
    stats = {'total': 0, 'open': 0, 'resolved': 0}

    # Always calculate fresh
    my_complaints = Complaint.query.filter_by(user_id=session['user_id']).order_by(Complaint.date.desc()).all()
    
    if request.method == 'POST':
        action = request.form.get('action', '')
        if action == 'file':
            description = request.form.get('description')
            category = request.form.get('category', 'General')
            priority = request.form.get('priority', 'Medium')
            if description:
                complaint_id = generate_complaint_id()
                new_complaint = Complaint(
                    id=complaint_id,
                    user_id=session['user_id'],
                    category=category,
                    priority=priority,
                    description=description,
                    status='Filed',
                    date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
                db.session.add(new_complaint)
                db.session.commit()
                ticket = complaint_id
                flash('Complaint filed successfully! Track ID: ' + complaint_id, 'success')
        elif action == 'track':
            tracking_id = request.form.get('track_id')
            complaint = Complaint.query.get(tracking_id)
            if complaint:
                status_message = f"Status: {complaint.status} | Category: {complaint.category} | Priority: {complaint.priority} | {complaint.description[:100]}..."
            else:
                status_message = "Complaint not found."

    stats = {
        'total': len(my_complaints),
        'open': len([c for c in my_complaints if c.status in ['Filed', 'In Progress']]),
        'resolved': len([c for c in my_complaints if c.status == 'Resolved'])
    }

    return render_template('complaints.html', 
                         ticket=ticket, 
                         status_message=status_message,
                         my_complaints=my_complaints,
                         categories=categories,
                         stats=stats)

@app.route('/bills')
def bills_page():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    unpaid_bills = Bill.query.filter(Bill.status != 'Paid').all()
    paid_bills = Bill.query.filter(Bill.status == 'Paid').all()
    total_outstanding = sum(int(bill.amount.replace('₹', '').replace(',', '')) for bill in unpaid_bills)
    total_paid = sum(int(bill.amount.replace('₹', '').replace(',', '')) for bill in paid_bills)
    average_bill = round((total_outstanding + total_paid) / Bill.query.count()) if Bill.query.count() else 0
    return render_template('bills.html', unpaid_bills=unpaid_bills, paid_bills=paid_bills, total_outstanding=total_outstanding, total_paid=total_paid, average_bill=average_bill)

@app.route('/admin_notices', methods=['GET', 'POST'])
def admin_notices():
    if 'logged_in' not in session or session.get('user_type') != 'admin':
        return redirect(url_for('login'))
    
    notices_list = Notice.query.order_by(Notice.date.desc()).all()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            title = request.form.get('title')
            date = request.form.get('date')
            content = request.form.get('content')
            new_notice = Notice(title=title, date=date, content=content)
            db.session.add(new_notice)
            db.session.commit()
            flash('Notice published successfully!', 'success')
        elif action == 'delete':
            title = request.form.get('title')
            notice = Notice.query.filter_by(title=title).first()
            if notice:
                db.session.delete(notice)
                db.session.commit()
            flash('Notice deleted!', 'success')
        return redirect(url_for('admin_notices'))
    
    return render_template('admin_notices.html', notices=notices_list)

@app.route('/notices')
def notices_page():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    notices_list = Notice.query.order_by(Notice.date.desc()).all()
    buildings_list = Building.query.all()
    return render_template('notices.html', notices=notices_list, buildings=buildings_list)

@app.route('/residents')
def residents_page():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    buildings_list = Building.query.all()
    return render_template('residents.html', buildings=buildings_list)
@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form.get('email')
        # Simple reset (just show message)
        flash('Password reset link sent to your email', 'success')
        return redirect(url_for('login'))

    return render_template('reset.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        if email and username and password:
            if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
                flash('Username or email already exists.', 'error')
                return render_template('register.html')
            new_user = User(username=username, email=email)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash(f'Account created for {username}! Login with your credentials.', 'success')
            return redirect(url_for('login'))
        flash('Please fill all fields.', 'error')
    return render_template('register.html')

@app.route('/building/<building_name>')
def building_detail(building_name):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    building = Building.query.get(building_name.replace('-', ' '))
    if not building:
        flash('Building not found.', 'error')
        return redirect(url_for('residents'))
    
    # Sample floor plans
    floor_plans = [
        {"floor": f"Floor {i}", "flats": 6, "vacant": random.randint(0,2), "amenities": ["Lift", "Stairs"]} for i in range(1, building.floors + 1)
    ]
    
    # Sample residents from DB
    sample_residents = Resident.query.filter_by(building=building.name).limit(3).all()
    
    # Sample maintenance (static)
    maintenance_tickets = [
        {"id": "MT-" + ''.join(random.choices(string.digits, k=6)), "issue": "Lift repair", "status": "Resolved", "date": "2024-04-15"},
        {"id": "MT-" + ''.join(random.choices(string.digits, k=6)), "issue": "Plumbing check", "status": "Pending", "date": "2024-05-01"}
    ]
    
    return render_template('building_detail.html', building=building, floor_plans=floor_plans, sample_residents=sample_residents, maintenance_tickets=maintenance_tickets)

def get_sample_residents(num=10):
    return [{"flat": f"A-{random.randint(101,125):03d}", "name": f"John Doe {random.randint(1,99)}", "family_size": random.randint(2,5)} for _ in range(num)]

@app.route('/profile')
def profile():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    return render_template('profile.html')

with app.app_context():
    db.create_all()
    seed_data()
    db.session.commit()

if __name__ == '__main__':
    app.run(debug=True, port=5002)

from flask import Flask, render_template, request, redirect, session, flash, url_for, make_response
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Customer, Application, PaymentProof, Permission, datetime, Notification, SalesLead, SenderID
import re
import random
import string
import os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from itsdangerous import URLSafeTimedSerializer
from datetime import datetime, timedelta
from sqlalchemy import func
from reportlab.pdfgen import canvas
from io import BytesIO
from flask import make_response
from flask import request, jsonify



app = Flask(__name__)
app.secret_key = "talksasa_secret_2026"

app.config["UPLOAD_FOLDER"] = "uploads"
serializer = URLSafeTimedSerializer(app.secret_key)

# ---------------- DATABASE ----------------

app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:happycrm%402026@localhost/talksasa"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# ----------------Talksasa EMAIL ----------------
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'janiotis909@gmail.com'
app.config['MAIL_PASSWORD'] = 'lilx ybcs ryoh lypq'
mail = Mail(app)

# role permission
def get_perm():
    role = session.get("role")
    if not role:
        return None
    return Permission.query.filter_by(role=role).first()

def generate_password():
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(6))

# CREATE TABLES STARTER USERS ----------------
with app.app_context():
    db.create_all()

    users = [
        ("superadmin", "admin123", "superadmin"),
        ("sales1", "1234", "sales"),
        ("tech1", "1234", "tech"),
    ]

    for username, password, role in users:
        existing_user = User.query.filter_by(username=username).first()

        if not existing_user:
            user = User(
                username=username,
                password_hash=generate_password_hash(password),
                role=role
            )
            db.session.add(user)

    db.session.commit()

    print("Database initialized + users created")

    # DEFAULT PERMISSIONS
    if not Permission.query.filter_by(role="superadmin").first():
        db.session.add(Permission(
            role="superadmin",
            can_view_dashboard=True,
            can_view_customers=True,
            can_create_customers=True,
            can_edit_customers=True,
            can_delete_customers=True,
            can_view_applications=True,
            can_create_applications=True,
            can_edit_applications=True,
            can_delete_applications=True,
            can_assign_applications=True,
            can_upload_pop=True,
            can_manage_permissions=True
        ))

    if not Permission.query.filter_by(role="sales").first():
        db.session.add(Permission(
            role="sales",
            can_view_dashboard=True,
            can_view_customers=True,
            can_create_customers=True,
            can_view_applications=True,
            can_create_applications=True,
            can_assign_applications=True
        ))

    if not Permission.query.filter_by(role="tech").first():
        db.session.add(Permission(
            role="tech",
            can_view_dashboard=True,
            can_view_customers=True,
            can_view_applications=True,
            can_upload_pop=True
        ))

    db.session.commit()

# LOGIN 
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        username = request.form["username"].strip()
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):

            # clear old session
            session.clear()

            # save new session
            session["logged_in"] = True
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role.lower().strip()

            flash("Login successful")

            # role redirects
            if session["role"] == "superadmin":
                return redirect(url_for("dashboard"))

            elif session["role"] == "sales":
                return redirect(url_for("sales_dashboard"))

            elif session["role"] == "tech":
                return redirect(url_for("tech_dashboard"))

            elif session["role"] == "customer":
                return redirect(url_for("customer_dashboard"))

            flash("Unknown role assigned")
            return redirect(url_for("login"))

        flash("Invalid username or password")
        return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/create_user", methods=["GET", "POST"])
def create_user():

    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if session.get("role") != "superadmin":
        return "Access Denied"

    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        role = request.form["role"].lower()

        existing = User.query.filter_by(username=username).first()

        if existing:
            flash("User already exists")
            return redirect(url_for("create_user"))

        new_user = User(
            username=username,
            password_hash=generate_password_hash(password),
            role=role
        )

        db.session.add(new_user)
        db.session.commit()

        flash("User created successfully")
        return redirect(url_for("create_user"))

    users = User.query.order_by(User.id.desc()).all()

    return render_template(
        "create_user.html",
        users=users
    )

@app.route("/edit_user/<int:user_id>", methods=["GET", "POST"])
def edit_user(user_id):

    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if session.get("role") != "superadmin":
        return "Access Denied"

    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        user.username = request.form["username"]
        user.role = request.form["role"]

        password = request.form.get("password")

        if password:
            user.password_hash = generate_password_hash(password)

        db.session.commit()

        flash("User updated successfully")
        return redirect(url_for("create_user"))

    return render_template(
        "edit_user.html",
        user=user
    )


@app.route("/delete_user/<int:user_id>")
def delete_user():

    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if session.get("role") != "superadmin":
        return "Access Denied"

    user = User.query.get_or_404(user_id)

    # Prevent deleting yourself
    if user.username == session.get("username"):
        flash("You cannot delete your own account.")
        return redirect(url_for("create_user"))

    db.session.delete(user)
    db.session.commit()

    flash("User deleted successfully.")
    return redirect(url_for("create_user"))

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully")
    return redirect(url_for("login"))
# ---------------- DASHBOARD ----------------
@app.route("/")
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    perm = get_perm()
    if not perm or not perm.can_view_dashboard:
        return "Access Denied"

    customers = Customer.query.all()
    applications = Application.query.all()

    return render_template("dashboard.html", customers=customers, applications=applications)

@app.route("/add_customer", methods=["GET", "POST"])
def add_customer():

    if not session.get("logged_in"):
        return redirect(url_for("login"))

    # role check
    if session.get("role") not in ["sales", "tech", "superadmin"]:
        return "Access Denied"

    if request.method == "POST":

        import re
        from flask_mail import Message
        from werkzeug.security import generate_password_hash

        name = request.form["name"]
        phone = request.form["phone"]
        email = request.form["email"].lower().strip()

# ---------------- PHONE VALIDATION ----------------
        if not re.match(r'^\+254(7|1)\d{8}$', phone):
           flash("Invalid phone format. Use +2547XXXXXXXX or +2541XXXXXXXX")
           return redirect(url_for("add_customer"))
            

        # ---------------- CHECK CUSTOMER EXISTS ----------------
        existing_customer = Customer.query.filter_by(email=email).first()
        if existing_customer:
            flash("Customer already exists")
            return redirect(url_for("add_customer"))

        # ---------------- CHECK USER EXISTS ----------------
        existing_user = User.query.filter_by(username=email).first()

        if existing_user:
            customer_user = existing_user
            password = None
        else:
            password = generate_password()

            customer_user = User(
                username=email,
                password_hash=generate_password_hash(password),
                role="customer"
            )

            db.session.add(customer_user)
            db.session.commit()

        # ---------------- CUSTOMER PROFILE ----------------
        customer = Customer(
            name=name,
            phone=phone,
            email=email,
            user_id=customer_user.id,
            created_by=session["user_id"]
        )

        db.session.add(customer)

        # ---------------- NOTIFICATIONS ----------------
        recipients = User.query.filter(
            User.role.in_(["tech", "superadmin"])
        ).all()

        for u in recipients:
            db.session.add(Notification(
                user_id=u.id,
                message=f"New customer created: {name} ({phone})"
            ))

        db.session.commit()

        # ---------------- EMAIL ONLY FOR NEW USER ----------------
        if password:
            msg = Message(
                subject="Welcome to Talksasa Customer Portal",
                sender=app.config["MAIL_USERNAME"],
                recipients=[email]
            )

            msg.html = f"""
            <div style="font-family: Arial; padding:20px;">
                <h2>Welcome to Talksasa CRM</h2>
                <p>Hello <b>{name}</b>,</p>
                <p>Your account has been created successfully.</p>
                <hr>
                <p><b>Login Email:</b> {email}</p>
                <p><b>Temporary Password:</b> {password}</p>
                <p><b>Login:</b> http://127.0.0.1:5000/customer_login</p>
                <br>
                Regards,<br>
                Talksasa Team
            </div>
            """

            mail.send(msg)

        flash("Customer created successfully!")
        return redirect(url_for("dashboard"))

    return render_template("add_customer.html")

# ---------------- VIEW CUSTOMERS ----------------
@app.route("/customers")
def view_customers():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    perm = get_perm()
    if not perm or not perm.can_view_customers:
        return "Access Denied"

    customers = Customer.query.all()
    return render_template("customers.html", customers=customers)

@app.route("/add_application", methods=["GET", "POST"])
def add_application():

    if not session.get("logged_in"):
        return redirect(url_for("login"))

    customers = Customer.query.all()

    if request.method == "POST":

        customer_id = int(request.form["customer_id"])
        company = request.form["company"]
        service = request.form["service"]
        sender_id = request.form["sender_id"]

        stream = request.form.get("stream")

        application = Application(
            customer_id=customer_id,
            company=company,
            service=service,
            sender_id=sender_id,
            created_by=session["user_id"],
            status="Pending",
            assigned_to=None,
            stream=stream
        )

        db.session.add(application)
        db.session.commit()

        flash("Application created successfully")
        return redirect(url_for("applications_list"))

    return render_template("add_application.html", customers=customers)

@app.route("/edit_application/<int:id>", methods=["GET", "POST"])
def edit_application(id):

    if not session.get("logged_in"):
        return redirect(url_for("login"))

    application = Application.query.get_or_404(id)
    customers = Customer.query.all()

    if request.method == "POST":

        application.customer_id = request.form["customer_id"]
        application.company = request.form["company"]
        application.service = request.form["service"]
        application.sender_id = request.form["sender_id"]
        application.stream = request.form.get("stream")

        db.session.commit()

        flash("Application updated successfully")
        return redirect(url_for("applications_list"))

    return render_template(
        "edit_application.html",
        application=application,
        customers=customers
    )

@app.route("/delete_application/<int:id>", methods=["POST"])
def delete_application(id):

    application = Application.query.get_or_404(id)

    db.session.delete(application)
    db.session.commit()

    flash("Application deleted successfully")
    return redirect(url_for("applications_list"))

# UPLOAD PAYMENT PROOF
@app.route("/upload_payment/<int:app_id>", methods=["POST"])
def upload_payment(app_id):
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    file = request.files.get("file")

    if file and file.filename:
        import os
        from werkzeug.utils import secure_filename

        filename = secure_filename(file.filename)

        if not os.path.exists(app.config["UPLOAD_FOLDER"]):
            os.makedirs(app.config["UPLOAD_FOLDER"])

        file.save(
            os.path.join(
                app.config["UPLOAD_FOLDER"],

                filename
            )
        )

        payment = PaymentProof(
            application_id=app_id,
            filename=filename,

            # this marks it as payment proof
            file_type="payment_proof"
        )

        db.session.add(payment)

        db.session.commit()

        flash("Payment proof uploaded successfully!")

    return redirect(
        url_for(
            "application_detail",
            id=app_id
        )
    )
# ---------------- APPLICATION LIST ----------------
@app.route("/applications")
def applications_list():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    perm = get_perm()
    if not perm or not perm.can_view_applications:
        return "Access Denied"

    applications = Application.query.all()

    tech_users = User.query.filter_by(role="tech").all()

    return render_template(
        "application.html",
        applications=applications,
        tech_users=tech_users
    )

# ---------------- SALES DASHBOARD ----------------
@app.route("/sales_dashboard")
def sales_dashboard():

    if not session.get("logged_in") or session.get("role") != "sales":
        return redirect(url_for("login"))

    user_id = session["user_id"]

    #customers = Customer.query.filter_by(created_by=user_id).all()
    customers = Customer.query.all()

    customer_ids = [c.id for c in customers]

    applications = Application.query.filter(
        Application.customer_id.in_(customer_ids)
    ).all()

    techs = User.query.filter_by(role="tech").all()

    notifications = Notification.query.filter_by(
        user_id=user_id
    ).order_by(Notification.created_at.desc()).all()

    return render_template(
        "sales_dashboard.html",
        customers=customers,
        applications=applications,
        techs=techs,
        notifications=notifications
    )

@app.route("/tech_dashboard")
def tech_dashboard():

    if not session.get("logged_in") or session.get("role") != "tech":
        return redirect(url_for("login"))

    user_id = session["user_id"]

    applications = Application.query.all()
    customers = Customer.query.all()

    notifications = Notification.query.filter_by(
        user_id=user_id,
        is_read=False
    ).order_by(Notification.created_at.desc()).all()

    perm = Permission.query.filter_by(role="tech").first()

    return render_template(
        "tech_dashboard.html",
        applications=applications,
        customers=customers,
        notifications=notifications,
        perm=perm
    )
# ---------------- PERMISSIONS ----------------
@app.route("/permissions", methods=["GET", "POST"])
def permissions():
    if session.get("role") != "superadmin":
        return redirect(url_for("login"))

    if request.method == "POST":
        role = request.form.get("role")

        perm = Permission.query.filter_by(role=role).first()
        if not perm:
            perm = Permission(role=role)
            db.session.add(perm)

        fields = [
            "can_view_dashboard",
            "can_view_customers", "can_create_customers", "can_edit_customers", "can_delete_customers",
            "can_view_applications", "can_create_applications", "can_edit_applications", "can_delete_applications",
            "can_assign_applications",
            "can_upload_pop",
            "can_manage_permissions"
        ]

        for f in fields:
            setattr(perm, f, True if request.form.get(f) else False)

        db.session.commit()
        flash("Permissions updated!")

    return render_template("permissions.html")

# ---------------- ASSIGN APPLICATION ----------------
@app.route("/assign_application/<int:id>", methods=["POST"])
def assign_application(id):
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    perm = get_perm()
    if not perm or not perm.can_assign_applications:
        return "Access Denied"

    app_record = Application.query.get_or_404(id)
    tech_id = request.form.get("tech_id")

    app_record.assigned_to = tech_id
    app_record.status = "Assigned"

    notification = Notification(
        user_id=tech_id,
        message=f"You have been assigned application for {app_record.customer.name} ({app_record.service})"
    )

    db.session.add(notification)
    db.session.commit()

    flash("Application assigned successfully!")
    return redirect(url_for("sales_dashboard"))


@app.route("/upload_document/<int:app_id>", methods=["POST"])
def upload_document(app_id):
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    file = request.files.get("file")

    if file and file.filename:
        import os
        from werkzeug.utils import secure_filename

        filename = secure_filename(file.filename)

        if not os.path.exists(app.config["UPLOAD_FOLDER"]):
            os.makedirs(app.config["UPLOAD_FOLDER"])

        file.save(
            os.path.join(
                app.config["UPLOAD_FOLDER"],
                filename
            )
        )

        document = PaymentProof(
            application_id=app_id,
            filename=filename,

            # marks as document
            file_type="document"
        )

        db.session.add(document)
        db.session.commit()

        flash("Document uploaded successfully!")

    return redirect(
        url_for(
            "application_detail",
            id=app_id
        )
    )


# ---------------- EDIT CUSTOMER ----------------
@app.route("/edit_customer/<int:id>", methods=["GET", "POST"])
def edit_customer(id):
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    perm = get_perm()
    if not perm or not perm.can_edit_customers:
        return "Access Denied"

    customer = Customer.query.get_or_404(id)

    if request.method == "POST":
        customer.name = request.form["name"]
        customer.phone = request.form["phone"]
        customer.email = request.form["email"]

        db.session.commit()
        flash("Customer updated!")
        return redirect(url_for("view_customers"))

    return render_template("edit_customer.html", customer=customer)

# ---------------- DELETE CUSTOMER ----------------
@app.route("/delete_customer/<int:id>", methods=["POST"])
def delete_customer(id):
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    perm = get_perm()
    if not perm or not perm.can_delete_customers:
        return "Access Denied"

    customer = Customer.query.get_or_404(id)

    for app in customer.applications:
        db.session.delete(app)

    db.session.delete(customer)
    db.session.commit()

    flash("Customer deleted!")
    return redirect(url_for("view_customers"))

@app.route("/application/<int:id>")
def application_detail(id):
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    application = Application.query.get_or_404(id)

    return render_template("application_detail.html", application=application)


# ---------------- UPDATE APPLICATION ----------------
@app.route("/update_application/<int:id>", methods=["POST"])
def update_application(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    perm = get_perm()
    if not perm or not perm.can_edit_applications:
        return "Access Denied"

    app_record = Application.query.get_or_404(id)

    if app_record.status in ["Completed", "Rejected"]:
        flash("Finalized application cannot be changed")
        return redirect(url_for("applications_list"))

    status = request.form.get("status")

    allowed = ["Pending", "In Progress", "Completed", "Rejected"]

    if status not in allowed:
        flash("Invalid status")
        return redirect(url_for("applications_list"))

    app_record.status = status
    db.session.commit()

    flash("Updated successfully")
    return redirect(url_for("applications_list"))



# ---------------- NOTIFICATION READ ----------------
@app.route("/notification/read/<int:id>", methods=["POST"])
def mark_notification_read(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    note = Notification.query.filter_by(
        id=id,
        user_id=session["user_id"]
    ).first_or_404()

    note.is_read = True
    db.session.commit()

    return redirect(url_for("tech_dashboard"))



# ----------------------------------
@app.route("/customer_login", methods=["GET", "POST"])
def customer_login():

    if request.method == "POST":

        email = request.form["email"].lower().strip()
        password = request.form["password"]

        # find customer user
        user = User.query.filter_by(
            username=email,
            role="customer"
        ).first()

        if user and check_password_hash(user.password_hash, password):

            session.clear()

            session["logged_in"] = True
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = "customer"

            flash("Login successful")
            return redirect(url_for("customer_dashboard"))

        flash("Invalid login details")
        return redirect(url_for("customer_login"))

    return render_template("customer_login.html")

# ---------------- CUSTOMER DASHBOARD ----------------
@app.route("/customer_dashboard")
def customer_dashboard():

    if not session.get("logged_in"):
        return redirect(url_for("customer_login"))

    user_id = session.get("user_id")

    customer = Customer.query.filter_by(user_id=user_id).first()

    if not customer:
        flash("Customer profile not found")
        return redirect(url_for("customer_login"))

    applications = Application.query.filter_by(customer_id=customer.id).all()

    total = len(applications)
    in_process = len([a for a in applications if a.status in ["Draft", "Sent"]])
    completed = len([a for a in applications if a.status == "Completed"])
    rejected = len([a for a in applications if a.status == "Rejected"])

    return render_template(
        "customer_dashboard.html",
        applications=applications,
        total=total,
        in_process=in_process,
        completed=completed,
        rejected=rejected
    )
@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():

    if request.method == "POST":
        email = request.form["email"]

        user = User.query.filter_by(username=email).first()

        if user:
            token = serializer.dumps(user.id, salt="reset-password")

            reset_link = url_for("reset_token", token=token, _external=True)

            from flask_mail import Message

            msg = Message(
                subject="Password Reset Request",
                sender=app.config["MAIL_USERNAME"],
                recipients=[email]
            )

            msg.body = f"""
Click the link below to reset your password:

{reset_link}

If you did not request this, ignore this email.
"""

            mail.send(msg)

        flash("If email exists, reset link has been sent.")
        return redirect(url_for("customer_login"))

    return render_template("reset_password.html")

@app.route("/reset/<token>", methods=["GET", "POST"])
def reset_token(token):

    try:
        user_id = serializer.loads(token, salt="reset-password", max_age=3600)
    except:
        return "Invalid or expired link"

    user = User.query.get(user_id)

    if request.method == "POST":
        new_password = request.form["password"]

        user.password_hash = generate_password_hash(new_password)

        db.session.commit()

        flash("Password updated successfully!")
        return redirect(url_for("customer_login"))

    return render_template("reset_form.html")

@app.route("/kanban")
def kanban():

    if not session.get("logged_in"):
        return redirect(url_for("login"))

    role = session.get("role")
    user_id = session.get("user_id")

    # ---------------- ROLE-BASED DATA ----------------
    if role == "superadmin":
        leads = SalesLead.query.all()

    elif role in ["sales", "tech"]:
        leads = SalesLead.query.filter_by(created_by=user_id).all()

    else:
        return "Access Denied"

    return render_template(
        "kanban.html",
        title="Sales Pipeline",
        items=leads,
        stages=[
            "New Lead",
            "Demo Scheduled",
            "Awaiting Decision",
            "Converted",
            "Lipa Mdogo",
            "Lost"
        ],
        update_route="update_lead_stage",
        show_form=True
    )


@app.route("/add_lead", methods=["POST"])
def add_lead():

    if not session.get("logged_in"):
        return redirect(url_for("login"))

    lead = SalesLead(
        name=request.form.get("name"),
        company=request.form.get("company"),
        phone=request.form.get("phone"),
        email=request.form.get("email"),
        created_by=session["user_id"],
        stage="New Lead"
    )

    db.session.add(lead)
    db.session.commit()

    flash("Lead added")
    return redirect(url_for("kanban"))


@app.route("/update_lead_stage/<int:id>", methods=["POST"])
def update_lead_stage(id):

    if not session.get("logged_in"):
        return redirect(url_for("login"))

    lead = SalesLead.query.get_or_404(id)
    lead.stage = request.form.get("stage")

    db.session.commit()

    return redirect(url_for("kanban"))

from flask import request, jsonify

@app.route("/update_lead_stage_drag/<int:id>", methods=["POST"])
def update_lead_stage_drag(id):

    if not session.get("logged_in"):
        return jsonify({"success": False}), 401

    lead = SalesLead.query.get_or_404(id)

    data = request.get_json()

    lead.stage = data.get("stage")

    db.session.commit()

    return jsonify({"success": True})


@app.route("/admin_report")
def admin_report():

    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if session.get("role") != "superadmin":
        return "Access Denied"

    # TOTAL LEADS
    total_leads = SalesLead.query.count()

    converted = SalesLead.query.filter_by(
        stage="Converted"
    ).count()

    lost = SalesLead.query.filter_by(
        stage="Lost"
    ).count()

    # GET USERS BY ROLE
    sales_users = User.query.filter_by(role="sales").all()
    tech_users = User.query.filter_by(role="tech").all()

    sales_leads = 0
    tech_leads = 0

    # SALES PERFORMANCE
    sales_performance = []

    for user in sales_users:
        total = SalesLead.query.filter_by(
            created_by=user.id
        ).count()

        conv = SalesLead.query.filter_by(
            created_by=user.id,
            stage="Converted"
        ).count()

        lost_leads = SalesLead.query.filter_by(
            created_by=user.id,
            stage="Lost"
        ).count()

        rate = (conv / total * 100) if total > 0 else 0

        sales_performance.append({
            "name": user.username,
            "total": total,
            "converted": conv,
            "lost": lost_leads,
            "rate": round(rate, 1)
        })

        sales_leads += total

    sales_performance = sorted(
        sales_performance,
        key=lambda x: x["rate"],
        reverse=True
    )

    # TECH PERFORMANCE
    tech_performance = []

    for user in tech_users:
        total = SalesLead.query.filter_by(
            created_by=user.id
        ).count()

        conv = SalesLead.query.filter_by(
            created_by=user.id,
            stage="Converted"
        ).count()

        lost_leads = SalesLead.query.filter_by(
            created_by=user.id,
            stage="Lost"
        ).count()

        rate = (conv / total * 100) if total > 0 else 0

        tech_performance.append({
            "name": user.username,
            "total": total,
            "converted": conv,
            "lost": lost_leads,
            "rate": round(rate, 1)
        })

        tech_leads += total

    tech_performance = sorted(
        tech_performance,
        key=lambda x: x["rate"],
        reverse=True
    )

    # TOP PERFORMERS

    top_sales = sales_performance[0] if sales_performance else None
    top_tech = tech_performance[0] if tech_performance else None

    # SENDER ID ANALYTICS

    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    weekly_sender_ids = SenderID.query.filter(
        SenderID.created_at >= week_ago
    ).count()

    monthly_sender_ids = SenderID.query.filter(
        SenderID.created_at >= month_ago
    ).count()

    total_sender_ids = SenderID.query.count()

    return render_template(
        "admin_report.html",

        total_leads=total_leads,
        sales_leads=sales_leads,
        tech_leads=tech_leads,
        converted=converted,
        lost=lost,

        weekly_sender_ids=weekly_sender_ids,
        monthly_sender_ids=monthly_sender_ids,
        total_sender_ids=total_sender_ids,

        sales_performance=sales_performance,
        tech_performance=tech_performance,

        top_sales=top_sales,
        top_tech=top_tech
    )

@app.route("/admin_report_pdf")
def admin_report_pdf():

    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if session.get("role") != "superadmin":
        return "Access Denied"

    buffer = BytesIO()
    p = canvas.Canvas(buffer)

    y = 800

    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, y, "TalkSasa Admin Report")
    y -= 40

    # totals
    p.setFont("Helvetica", 12)
    p.drawString(50, y, f"Total Leads: {SalesLead.query.count()}")
    y -= 25

    p.drawString(
        50, y,
        f"Converted: {SalesLead.query.filter_by(stage='Converted').count()}"
    )
    y -= 25

    p.drawString(
        50, y,
        f"Lost: {SalesLead.query.filter_by(stage='Lost').count()}"
    )
    y -= 40

    # sender ids
    p.drawString(50, y, f"Total Sender IDs: {SenderID.query.count()}")
    y -= 40

    # sales team
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Sales Team Performance")
    y -= 30

    p.setFont("Helvetica", 12)

    sales_users = User.query.filter_by(role="sales").all()

    for user in sales_users:
        total = SalesLead.query.filter_by(created_by=user.id).count()
        converted = SalesLead.query.filter_by(
            created_by=user.id,
            stage="Converted"
        ).count()

        p.drawString(
            70,
            y,
            f"{user.username}: {total} leads | {converted} converted"
        )
        y -= 20

    y -= 20

    # tech team
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Tech Team Performance")
    y -= 30

    p.setFont("Helvetica", 12)

    tech_users = User.query.filter_by(role="tech").all()

    for user in tech_users:
        total = SalesLead.query.filter_by(created_by=user.id).count()
        converted = SalesLead.query.filter_by(
            created_by=user.id,
            stage="Converted"
        ).count()

        p.drawString(
            70,
            y,
            f"{user.username}: {total} leads | {converted} converted"
        )
        y -= 20

    p.save()

    pdf = buffer.getvalue()
    buffer.close()

    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = \
        "attachment; filename=admin_report.pdf"

    return response


# SEND TO PROVIDER (UPDATED)
@app.route("/send_to_provider/<int:app_id>", methods=["POST"])
def send_to_provider(app_id):

    application = Application.query.get_or_404(app_id)

    # SAFETY CHECK
    if not application.payment_proofs:
        flash("Please upload documents/payment before sending.")
        return redirect(url_for("application_detail", id=app_id))

    # STREAM EMAIL MAP
    STREAM_EMAILS = {
        "Bumble Bee": "bumblebee@gmail.com",
        "Lady Bird": "ladybird@gmail.com"
    }

    provider_email = STREAM_EMAILS.get(application.stream)

    if not provider_email:
        flash("Stream not set or invalid. Check application stream.")
        return redirect(url_for("application_detail", id=app_id))

    # FORM DATA
    subject = request.form.get("subject") or f"New Application #{application.id}"
    body = request.form.get("body") or ""

    cc_raw = request.form.get("cc", "")
    cc_list = [email.strip() for email in cc_raw.split(",") if email.strip()]

    # COLLECT FILES
    documents = []
    payments = []

    for file in application.payment_proofs:
        if file.file_type == "document":
            documents.append(file.filename)
        elif file.file_type == "payment_proof":
            payments.append(file.filename)

    # CREATE EMAIL
    msg = Message(
        subject=subject,
        sender=app.config['MAIL_USERNAME'],
        recipients=[provider_email],
        cc=cc_list
    )

    # HTML EMAIL BODY
    msg.html = f"""
    <div style="font-family:Arial; font-size:14px; color:#333;">

        <p>{body}</p>

        <hr>

        <p><b>Customer:</b> {application.customer.name}</p>
        <p><b>Company:</b> {application.company}</p>
        <p><b>Service:</b> {application.service}</p>
        <p><b>Stream:</b> {application.stream}</p>

        <p><b>Application ID:</b> #{application.id}</p>

    </div>
    """

    # ATTACH FILES
    for f in documents + payments:
        path = os.path.join("uploads", f)
        if os.path.exists(path):
            with app.open_resource(path) as fp:
                msg.attach(f, "application/octet-stream", fp.read())

    
    # SIGNATURE
    msg.html += """
    <br><br><br>
    <div style="text-align:center; border-top:1px solid #eee; padding-top:15px;">

        <img src="https://your-domain.com/static/talksasa-logo.png"
             style="width:120px; margin-bottom:8px;">

        <p style="font-size:12px; color:#777; margin:0;">
            TalkSasa CRM
        </p>

        <p style="font-size:11px; color:#aaa;">
            Automating your workflow
        </p>

    </div>
    """

    # SEND EMAIL
    mail.send(msg)

    # UPDATE APPLICATION STATUS
    application.status = "Sent"
    application.sent_to_provider = True
    application.sent_at = datetime.now(timezone.utc)

    db.session.commit()

    flash(f"Application sent successfully via {application.stream}!")
    return redirect(url_for("application_detail", id=app_id))

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)


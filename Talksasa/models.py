from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# =====================================================
# USERS
# =====================================================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Applications created by user
    created_applications = db.relationship(
        "Application",
        foreign_keys="Application.created_by",
        back_populates="created_by_user"
    )

    # Applications assigned to user
    assigned_applications = db.relationship(
        "Application",
        foreign_keys="Application.assigned_to",
        back_populates="assigned_to_user"
    )

    # Notifications
    notifications = db.relationship(
        "Notification",
        back_populates="user"
    )


# =====================================================
# CUSTOMERS
# =====================================================
class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Applications linked to customer
    applications = db.relationship(
        "Application",
        back_populates="customer"
    )


# =====================================================
# APPLICATIONS
# =====================================================
class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))

    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'))

    company = db.Column(db.String(100))
    service = db.Column(db.String(100))
    sender_id = db.Column(db.String(50))

    status = db.Column(db.String(50))
    date_applied = db.Column(db.DateTime, default=datetime.utcnow)

    stream = db.Column(db.String(50))

    # User relationships
    created_by_user = db.relationship(
        "User",
        foreign_keys=[created_by],
        back_populates="created_applications"
    )

    assigned_to_user = db.relationship(
        "User",
        foreign_keys=[assigned_to],
        back_populates="assigned_applications"
    )

    # Customer relationship
    customer = db.relationship(
        "Customer",
        back_populates="applications"
    )

    # Payment/document relationship
    payment_proofs = db.relationship(
        "PaymentProof",
        back_populates="application",
        cascade="all, delete-orphan"
    )


# =====================================================
# PAYMENT PROOF / DOCUMENTS
# =====================================================
class PaymentProof(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    application_id = db.Column(
        db.Integer,
        db.ForeignKey('application.id')
    )

    filename = db.Column(db.String(200))
    file_type = db.Column(db.String(50))   # "document" or "payment_proof"

    upload_date = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    application = db.relationship(
        "Application",
        back_populates="payment_proofs"
    )


# =====================================================
# PERMISSIONS
# =====================================================
class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    role = db.Column(db.String(50), unique=True)

    can_view_dashboard = db.Column(db.Boolean, default=False)

    can_view_customers = db.Column(db.Boolean, default=False)
    can_create_customers = db.Column(db.Boolean, default=False)
    can_edit_customers = db.Column(db.Boolean, default=False)
    can_delete_customers = db.Column(db.Boolean, default=False)

    can_view_applications = db.Column(db.Boolean, default=False)
    can_create_applications = db.Column(db.Boolean, default=False)
    can_edit_applications = db.Column(db.Boolean, default=False)
    can_delete_applications = db.Column(db.Boolean, default=False)

    can_assign_applications = db.Column(db.Boolean, default=False)
    can_upload_pop = db.Column(db.Boolean, default=False)

    can_manage_permissions = db.Column(db.Boolean, default=False)


# =====================================================
# NOTIFICATIONS
# =====================================================
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id')
    )

    message = db.Column(db.String(255))
    is_read = db.Column(db.Boolean, default=False)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    user = db.relationship(
        "User",
        back_populates="notifications"
    )

class SenderID(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    client_name = db.Column(db.String(100))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    assigned_to = db.Column(db.Integer, nullable=True)

    
# =====================================================
# SALES KANBAN
# =====================================================
class SalesLead(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)
    company = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))

    stage = db.Column(
        db.String(50),
        default="New Lead"
    )

    notes = db.Column(db.Text)

    created_by = db.Column(
        db.Integer,
        db.ForeignKey("user.id")
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )
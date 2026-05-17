"""Initial migration - create all tables

Revision ID: 001_initial
Revises: 
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Users
    op.create_table('users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('full_name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(150), unique=True, nullable=False),
        sa.Column('phone', sa.String(20)),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('role', sa.Enum('user','admin', name='userrole'), default='user'),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    # Contacts
    op.create_table('contacts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('full_name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(150), nullable=False),
        sa.Column('phone', sa.String(20)),
        sa.Column('service', sa.String(100)),
        sa.Column('message', sa.Text()),
        sa.Column('is_read', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Bookings
    op.create_table('bookings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('full_name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(150), nullable=False),
        sa.Column('phone', sa.String(20)),
        sa.Column('service_type', sa.String(100)),
        sa.Column('booking_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('duration_mins', sa.Integer(), default=30),
        sa.Column('status', sa.Enum('pending','confirmed','cancelled','completed', name='bookingstatus'), default='pending'),
        sa.Column('notes', sa.Text()),
        sa.Column('google_event_id', sa.String(255)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Payments
    op.create_table('payments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('booking_id', sa.Integer(), sa.ForeignKey('bookings.id'), nullable=True),
        sa.Column('plan_name', sa.String(100), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(10), default='INR'),
        sa.Column('razorpay_order_id', sa.String(255), unique=True),
        sa.Column('razorpay_payment_id', sa.String(255)),
        sa.Column('razorpay_signature', sa.String(500)),
        sa.Column('status', sa.Enum('pending','success','failed','refunded', name='paymentstatus'), default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Blogs
    op.create_table('blogs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), unique=True, nullable=False),
        sa.Column('summary', sa.Text()),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tag', sa.String(50)),
        sa.Column('author', sa.String(100), default='CareerPilot Team'),
        sa.Column('is_published', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Resume Analyses
    op.create_table('resume_analyses',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('filename', sa.String(255)),
        sa.Column('role', sa.String(100)),
        sa.Column('total_score', sa.Integer()),
        sa.Column('keyword_score', sa.Integer()),
        sa.Column('structure_score', sa.Integer()),
        sa.Column('grade', sa.String(5)),
        sa.Column('feedback_json', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

def downgrade():
    op.drop_table('resume_analyses')
    op.drop_table('blogs')
    op.drop_table('payments')
    op.drop_table('bookings')
    op.drop_table('contacts')
    op.drop_table('users')

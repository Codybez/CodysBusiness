"""class

Revision ID: 6888a0e710ab
Revises: 0190e69abb6c
Create Date: 2023-08-28 09:37:25.440689

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6888a0e710ab'
down_revision = '0190e69abb6c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('business_profile',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('business_name', sa.String(length=100), nullable=False),
    sa.Column('business_type', sa.String(length=100), nullable=False),
    sa.Column('city', sa.String(length=100), nullable=False),
    sa.Column('suburb', sa.String(length=100), nullable=False),
    sa.Column('street', sa.String(length=100), nullable=False),
    sa.Column('number', sa.String(length=10), nullable=False),
    sa.Column('phone_number', sa.String(length=20), nullable=False),
    sa.Column('first_name', sa.String(length=50), nullable=False),
    sa.Column('last_name', sa.String(length=50), nullable=False),
    sa.Column('profile_pic', sa.String(length=100), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('business_profile')
    # ### end Alembic commands ###

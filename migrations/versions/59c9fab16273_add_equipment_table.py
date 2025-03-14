"""add equipment table

Revision ID: 59c9fab16273
Revises: ccd8131e7a99
Create Date: 2025-03-13 01:45:39.256724

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '59c9fab16273'
down_revision = 'ccd8131e7a99'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('gear_post',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=100), nullable=False),
    sa.Column('equipment_type', sa.String(length=50), nullable=False),
    sa.Column('location', sa.String(length=50), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('is_rental', sa.Boolean(), nullable=True),
    sa.Column('price', sa.Float(), nullable=True),
    sa.Column('rental_duration', sa.String(length=20), nullable=True),
    sa.Column('image_url', sa.String(length=200), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('gear_post')
    # ### end Alembic commands ###

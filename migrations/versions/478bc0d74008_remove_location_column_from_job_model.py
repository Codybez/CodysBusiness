"""Remove location column from Job model

Revision ID: 478bc0d74008
Revises: 290640f4d666
Create Date: 2024-11-25 17:32:03.793426

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '478bc0d74008'
down_revision = '290640f4d666'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('company_details',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('business_type', sa.String(length=100), nullable=False),
    sa.Column('nzbn', sa.String(length=100), nullable=True),
    sa.Column('director_first_name', sa.String(length=50), nullable=False),
    sa.Column('director_last_name', sa.String(length=50), nullable=False),
    sa.Column('physical_address', sa.String(length=100), nullable=False),
    sa.Column('unit_no', sa.String(length=10), nullable=True),
    sa.Column('trading_name', sa.String(length=100), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id')
    )
    with op.batch_alter_table('job', schema=None) as batch_op:
        batch_op.alter_column('job_category',
               existing_type=sa.VARCHAR(length=100),
               nullable=True)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('job', schema=None) as batch_op:
        batch_op.alter_column('job_category',
               existing_type=sa.VARCHAR(length=100),
               nullable=False)

    op.drop_table('company_details')
    # ### end Alembic commands ###

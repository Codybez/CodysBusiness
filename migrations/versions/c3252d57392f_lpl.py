"""lpl

Revision ID: c3252d57392f
Revises: c184170f946a
Create Date: 2024-01-23 13:42:14.941578

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3252d57392f'
down_revision = 'c184170f946a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('job', schema=None) as batch_op:
        batch_op.drop_column('date')
        batch_op.drop_column('street')
        batch_op.drop_column('end_time')
        batch_op.drop_column('start_time')
        batch_op.drop_column('number')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('job', schema=None) as batch_op:
        batch_op.add_column(sa.Column('number', sa.VARCHAR(length=10), nullable=False))
        batch_op.add_column(sa.Column('start_time', sa.TIME(), nullable=False))
        batch_op.add_column(sa.Column('end_time', sa.TIME(), nullable=False))
        batch_op.add_column(sa.Column('street', sa.VARCHAR(length=100), nullable=False))
        batch_op.add_column(sa.Column('date', sa.DATE(), nullable=False))

    # ### end Alembic commands ###

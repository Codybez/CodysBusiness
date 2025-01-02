"""addcategories

Revision ID: c71a10b7c55d
Revises: a893b2430b66
Create Date: 2024-12-30 15:22:38.965912

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c71a10b7c55d'
down_revision = 'a893b2430b66'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('labourer_profile', schema=None) as batch_op:
        batch_op.add_column(sa.Column('job_categories', sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column('job_locations', sa.String(length=500), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('labourer_profile', schema=None) as batch_op:
        batch_op.drop_column('job_locations')
        batch_op.drop_column('job_categories')

    # ### end Alembic commands ###

"""addcity_suburb

Revision ID: 16bc5e8f6e31
Revises: 04ce004aa979
Create Date: 2025-03-14 01:21:46.786175

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '16bc5e8f6e31'
down_revision = '04ce004aa979'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('gear_post', schema=None) as batch_op:
        batch_op.add_column(sa.Column('city_suburb', sa.String(length=50), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('gear_post', schema=None) as batch_op:
        batch_op.drop_column('city_suburb')

    # ### end Alembic commands ###

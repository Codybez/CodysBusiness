"""Add receiver_id to Message model

Revision ID: a63773ec222d
Revises: e642e4bd643f
Create Date: 2024-12-03 13:40:48.582026

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a63773ec222d'
down_revision = 'e642e4bd643f'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('message', schema=None) as batch_op:
        batch_op.add_column(sa.Column('receiver_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_message_receiver_user',
            'user',
            ['receiver_id'],
            ['id']
        )

def downgrade():
    with op.batch_alter_table('message', schema=None) as batch_op:
        batch_op.drop_constraint('fk_message_receiver_user', type_='foreignkey')
        batch_op.drop_column('receiver_id')

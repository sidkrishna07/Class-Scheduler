"""Add teacher_id foreign key to Course model

Revision ID: c5781e6bf9de
Revises: 
Create Date: 2024-11-16 19:11:08.066122

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c5781e6bf9de'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto-generated by Alembic - please adjust! ###
    with op.batch_alter_table('course', schema=None) as batch_op:
        # Adding the new teacher_id column
        batch_op.add_column(sa.Column('teacher_id', sa.Integer(), nullable=True))
        
        # Altering the time column to have a maximum length of 50 characters
        batch_op.alter_column(
            'time',
            existing_type=sa.TEXT(),
            type_=sa.String(length=50),
            existing_nullable=True
        )

    batch_op.create_foreign_key(
        'fk_course_teacher',  # Name of the foreign key constraint
        'user',               # Referenced table
        ['teacher_id'],        # Local column
        ['id']                 # Referenced column
    )
    batch_op.drop_column('teacher')


    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('course', schema=None) as batch_op:
        batch_op.add_column(sa.Column('teacher', sa.TEXT(), nullable=True))
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.alter_column('time',
               existing_type=sa.String(length=50),
               type_=sa.TEXT(),
               existing_nullable=True)
        batch_op.drop_column('teacher_id')

    # ### end Alembic commands ###
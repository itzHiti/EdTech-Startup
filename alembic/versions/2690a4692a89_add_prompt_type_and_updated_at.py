# alembic/versions/2690a4692a89_add_prompt_type_and_updated_at.py

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    # Step 1: Add column as NULLABLE first
    op.add_column('prompts', sa.Column(
        'prompt_type',
        sa.String(length=20),
        nullable=True,          # ← nullable first so existing rows don't crash
    ))

    # Step 2: Fill existing rows with default value
    op.execute("UPDATE prompts SET prompt_type = 'image' WHERE prompt_type IS NULL")

    # Step 3: Now make it NOT NULL
    op.alter_column('prompts', 'prompt_type', nullable=False)

    # updated_at is fine as nullable — no change needed here
    op.add_column('prompts', sa.Column(
        'updated_at',
        sa.DateTime(timezone=True),
        nullable=True,
    ))

    op.create_index('ix_prompts_prompt_type', 'prompts', ['prompt_type'])
    op.create_index('ix_prompts_user_id', 'prompts', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_prompts_user_id', table_name='prompts')
    op.drop_index('ix_prompts_prompt_type', table_name='prompts')
    op.drop_column('prompts', 'updated_at')
    op.drop_column('prompts', 'prompt_type')
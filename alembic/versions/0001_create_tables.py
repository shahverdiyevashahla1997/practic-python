"""Create users, habits and completion tables."""
from alembic import op
import sqlalchemy as sa

revision = "0001_create_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reminder_hour", sa.Integer(), nullable=False),
        sa.Column("reminder_minute", sa.Integer(), nullable=False),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)
    op.create_table("habits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("successful_completions", sa.Integer(), nullable=False),
        sa.Column("target_completions", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_habits_user_id", "habits", ["user_id"])
    op.create_table("habit_completions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("habit_id", sa.Integer(), sa.ForeignKey("habits.id", ondelete="CASCADE"), nullable=False),
        sa.Column("completion_date", sa.Date(), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("habit_id", "completion_date", name="uq_habit_completion_date"),
    )
    op.create_index("ix_habit_completions_habit_id", "habit_completions", ["habit_id"])


def downgrade():
    op.drop_index("ix_habit_completions_habit_id", table_name="habit_completions")
    op.drop_table("habit_completions")
    op.drop_index("ix_habits_user_id", table_name="habits")
    op.drop_table("habits")
    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_table("users")

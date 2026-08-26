import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("accounts", "0003_permissionoverride"), ("auth", "0012_alter_user_first_name_max_length")]
    operations = [
        migrations.CreateModel(
            name="RoleProfile",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("description", models.CharField(blank=True, max_length=240)),
                ("is_system", models.BooleanField(default=False)),
                ("is_owner", models.BooleanField(default=False)),
                ("group", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="casaviva_profile", to="auth.group")),
            ],
            options={"ordering": ["group__name"]},
        ),
    ]

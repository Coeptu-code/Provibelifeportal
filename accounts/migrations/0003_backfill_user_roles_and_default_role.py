from django.db import migrations, models


def backfill_user_roles(apps, schema_editor):
    User = apps.get_model("accounts", "User")

    for user in User.objects.all():
        if user.customer_id:
            role = "customer_user"
        elif getattr(user, "is_warehouse_staff", False):
            role = "warehouse_staff"
        elif user.is_superuser or user.is_staff or getattr(user, "is_ops_user", False):
            role = "admin"
        else:
            role = "admin"

        user.role = role
        if role != "customer_user":
            user.customer_id = None
        user.is_customer_user = role == "customer_user"
        user.is_warehouse_staff = role == "warehouse_staff"
        user.is_ops_user = role in {"warehouse_staff", "admin"}
        if role in {"warehouse_staff", "admin"}:
            user.is_staff = True
        user.save(
            update_fields=[
                "role",
                "customer",
                "is_customer_user",
                "is_warehouse_staff",
                "is_ops_user",
                "is_staff",
            ]
        )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_alter_user_options_user_is_warehouse_staff_user_role_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("customer_user", "Customer User"),
                    ("warehouse_staff", "Warehouse Staff"),
                    ("admin", "Admin"),
                ],
                db_index=True,
                default="admin",
                max_length=32,
            ),
        ),
        migrations.RunPython(backfill_user_roles, migrations.RunPython.noop),
    ]

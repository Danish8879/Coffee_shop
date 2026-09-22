from django.conf import settings
from django.db import migrations


# Users sign up with their email as username; copy it into the email field where it is missing
# so password reset and verification emails can find them.
def fill_missing_emails(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split('.'))
    for user in User.objects.filter(email='', username__contains='@'):
        user.email = user.username.lower()
        user.save(update_fields=['email'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_create_profiles_for_existing_users'),
    ]

    operations = [
        migrations.RunPython(fill_missing_emails, migrations.RunPython.noop),
    ]

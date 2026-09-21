from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderitem',
            name='grind',
            field=models.CharField(default='whole-beans', max_length=30),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='weight',
            field=models.PositiveIntegerField(default=250),
        ),
    ]

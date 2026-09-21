# Generated manually to allow products without an optional photo.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_category_alter_product_image_alter_product_category'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='image',
            field=models.ImageField(blank=True, upload_to='products/'),
        ),
    ]

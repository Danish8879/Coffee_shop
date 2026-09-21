from decimal import Decimal

from django.db import migrations


# Add the five starter bean products for new project databases.
def seed_coffee_beans(apps, schema_editor):
    Category = apps.get_model('products', 'Category')
    Product = apps.get_model('products', 'Product')
    category, _ = Category.objects.get_or_create(name='Coffee Beans', slug='coffee-beans')
    beans = [
        ('Attikan Estate', 'Chocolate-forward estate coffee with gentle citrus notes and a smooth, balanced finish.', Decimal('600.00')),
        ('Araku Estate', 'A bright, fruity coffee with a clean body and a sweet, lingering finish.', Decimal('550.00')),
        ('Baarbara Estate', 'Rich and rounded coffee with cocoa notes, mild acidity, and comforting warmth.', Decimal('600.00')),
        ('Harley Estate', 'Full-bodied estate coffee with caramel sweetness, soft spice, and a velvety finish.', Decimal('650.00')),
        ('Monsoon Malabar', 'Low-acidity Indian coffee with earthy spice, heavy body, and a mellow finish.', Decimal('400.00')),
    ]

    for name, description, price in beans:
        Product.objects.update_or_create(
            category=category,
            name=name,
            defaults={
                'description': description,
                'price': price,
                'image': '',
            },
        )


# Remove the starter bean products if this data migration is reversed.
def remove_seeded_coffee_beans(apps, schema_editor):
    Product = apps.get_model('products', 'Product')
    Product.objects.filter(name__in=[
        'Attikan Estate',
        'Araku Estate',
        'Baarbara Estate',
        'Harley Estate',
        'Monsoon Malabar',
    ]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0003_alter_product_image'),
    ]

    operations = [
        migrations.RunPython(seed_coffee_beans, remove_seeded_coffee_beans),
    ]

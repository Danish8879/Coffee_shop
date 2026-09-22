from decimal import Decimal

from django.db import migrations


CANNED_COFFEE = [
    ('Bold and Strong', 'Classic iced americano, dark roast and medium acidity.', Decimal('200.00')),
    ('Spanish Latte', 'Sweet canned latte with a hint of spicy cinnamon.', Decimal('300.00')),
    ('Pumpkin Punch', 'Iced americano with pumpkin spice.', Decimal('400.00')),
]

BREWING_EQUIPMENT = [
    ('French Press', 'Classic plunger brewer for a full-bodied, rich cup of coffee.', Decimal('1500.00')),
    ('Moka Pot', 'Stovetop brewer that makes strong, espresso-style coffee.', Decimal('2000.00')),
]


# Add the starter canned coffee and brewing equipment products for new project databases.
def seed_canned_coffee_and_brewing_equipment(apps, schema_editor):
    Category = apps.get_model('products', 'Category')
    Product = apps.get_model('products', 'Product')

    catalogue = [
        ('Canned Coffee', 'canned-coffee', CANNED_COFFEE),
        ('Brewing Equipment', 'brewing-equipment', BREWING_EQUIPMENT),
    ]

    for category_name, category_slug, products in catalogue:
        category, _ = Category.objects.get_or_create(slug=category_slug, defaults={'name': category_name})

        for name, description, price in products:
            Product.objects.update_or_create(
                category=category,
                name=name,
                defaults={
                    'description': description,
                    'price': price,
                    'image': '',
                },
            )


# Remove the starter canned coffee and brewing equipment products if this data migration is reversed.
def remove_seeded_canned_coffee_and_brewing_equipment(apps, schema_editor):
    Product = apps.get_model('products', 'Product')
    Product.objects.filter(
        name__in=[name for name, _, _ in CANNED_COFFEE + BREWING_EQUIPMENT],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0004_seed_coffee_beans'),
    ]

    operations = [
        migrations.RunPython(
            seed_canned_coffee_and_brewing_equipment,
            remove_seeded_canned_coffee_and_brewing_equipment,
        ),
    ]

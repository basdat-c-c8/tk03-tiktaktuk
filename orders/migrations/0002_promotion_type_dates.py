# Generated for TK03 final promotion compliance.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='promotion',
            name='discount_type',
            field=models.CharField(
                choices=[('nominal', 'Nominal'), ('percentage', 'Persentase')],
                default='nominal',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='promotion',
            name='start_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='promotion',
            name='end_date',
            field=models.DateField(blank=True, null=True),
        ),
    ]

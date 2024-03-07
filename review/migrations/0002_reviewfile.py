# Generated by Django 5.0.2 on 2024-03-04 18:03

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('file', '0001_initial'),
        ('review', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReviewFile',
            fields=[
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('updated_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('file', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, primary_key=True, serialize=False, to='file.file')),
            ],
            options={
                'db_table': 'tbl_review_file',
            },
        ),
    ]

# Generated by Django 5.1.6 on 2025-03-19 12:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('media_app', '0002_mediaproject_qr_code'),
    ]

    operations = [
        migrations.AddField(
            model_name='mediaproject',
            name='drive_link',
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
    ]

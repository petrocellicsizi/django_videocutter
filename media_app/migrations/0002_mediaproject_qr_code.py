# Generated by Django 5.1.6 on 2025-03-10 17:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('media_app', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='mediaproject',
            name='qr_code',
            field=models.FileField(blank=True, null=True, upload_to='qrcodes/'),
        ),
    ]

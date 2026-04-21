from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('detector', '0002_alter_detectionrecord_result'),
    ]

    operations = [
        migrations.AddField(
            model_name='detectionrecord',
            name='notes',
            field=models.TextField(blank=True),
        ),
    ]

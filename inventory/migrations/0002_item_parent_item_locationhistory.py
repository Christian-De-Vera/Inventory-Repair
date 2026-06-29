import django.db.models.deletion
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='item',
            name='parent_item',
            field=models.ForeignKey(blank=True, help_text='The assembly or kit this item belongs to', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='children', to='inventory.item'),
        ),
        migrations.CreateModel(
            name='LocationHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('moved_at', models.DateTimeField(auto_now_add=True)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='location_history', to='inventory.item')),
                ('location', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='inventory.location')),
            ],
            options={
                'verbose_name_plural': 'Location Histories',
                'ordering': ['-moved_at'],
            },
        ),
    ]
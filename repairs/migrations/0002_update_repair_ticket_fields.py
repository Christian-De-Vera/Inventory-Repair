from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0001_initial'),
        ('repairs', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='repairticket',
            name='assigned_to',
        ),
        migrations.RemoveField(
            model_name='repairticket',
            name='reported_by',
        ),
        migrations.AddField(
            model_name='repairticket',
            name='actual_cost',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=10, verbose_name='Actual Cost'),
        ),
        migrations.AddField(
            model_name='repairticket',
            name='estimated_cost',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=10, verbose_name='Estimated Cost'),
        ),
        migrations.AddField(
            model_name='repairticket',
            name='expected_completion_date',
            field=models.DateField(blank=True, null=True, verbose_name='Expected Completion'),
        ),
        migrations.AddField(
            model_name='repairticket',
            name='assigned_to',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_tickets', to='inventory.person', verbose_name='Assigned Technician'),
        ),
        migrations.AddField(
            model_name='repairticket',
            name='reported_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reported_tickets', to='inventory.person', verbose_name='Reported By'),
        ),
    ]
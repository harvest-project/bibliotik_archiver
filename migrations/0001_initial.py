# Generated by Django 2.1.7 on 2019-03-24 23:56

from django.db import migrations, models


def create_initial_archiver_state(apps, schema_editor):
    BibliotikArchiverState = apps.get_model('bibliotik_archiver', 'BibliotikArchiverState')
    BibliotikArchiverState.objects.create(
        is_enabled=True,
        last_meta_tracker_id=1,
    )


class Migration(migrations.Migration):
    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BibliotikArchiverState',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_enabled', models.BooleanField()),
                ('last_meta_tracker_id', models.BigIntegerField()),
            ],
        ),
        migrations.RunPython(create_initial_archiver_state, migrations.RunPython.noop),
    ]

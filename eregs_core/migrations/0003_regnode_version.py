# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-06-10 21:19
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eregs_core', '0002_regnode_node_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='regnode',
            name='version',
            field=models.CharField(default='', max_length=250),
            preserve_default=False,
        ),
    ]

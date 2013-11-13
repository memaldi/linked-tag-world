# coding=utf-8

from ltwserver import celery

from celery import current_task

@celery.task()
def generate_config_file(data_source, rdf_data=None, rdf_format=None, sparql_url=None, sparql_graph=None):
    from time import sleep
    current_task.update_state(state='PROGRESS', meta={'progress_percent': 20, 'progress_msg': 'Peeling potatoes...'})
    print 'Peeling potatoes...'
    sleep(3)
    current_task.update_state(state='PROGRESS', meta={'progress_percent': 50, 'progress_msg': 'Frying potatoes...'})
    print 'Frying potatoes...'
    sleep(5)
    current_task.update_state(state='PROGRESS', meta={'progress_percent': 55, 'progress_msg': 'Adding onion...'})
    print 'Adding onion...'
    sleep(2)
    current_task.update_state(state='PROGRESS', meta={'progress_percent': 60, 'progress_msg': 'Stirring eggs...'})
    print 'Stirring eggs...'
    sleep(3)
    current_task.update_state(state='PROGRESS', meta={'progress_percent': 75, 'progress_msg': 'Mixing all...'})
    print 'Mixing all...'
    sleep(3)
    current_task.update_state(state='PROGRESS', meta={'progress_percent': 90, 'progress_msg': 'Doing the homellette...'}) 
    print 'Doing the homellette...'
    sleep(2)

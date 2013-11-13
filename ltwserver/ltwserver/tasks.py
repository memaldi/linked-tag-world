# coding=utf-8

from ltwserver import celery

@celery.Task
def validate_sparql_endpoint():
    pass
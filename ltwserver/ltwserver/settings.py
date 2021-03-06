SECRET_KEY='\x05l%\xfeY3\xb2\xf9>\xba\xd9\xbfR\x82\xa3\xfd*lX>\x8a\x11\x98\xce'
CELERY_BROKER_URL='amqp://guest:guest@localhost:5672/'
#CELERY_BROKER_URL='redis://localhost:6379/0'
CELERY_RESULT_BACKEND='amqp://guest:guest@localhost:5672/'
#CELERY_RESULT_BACKEND='redis://localhost:6379/0'
CELERY_TASK_SERIALIZER='json'
CELERY_RESULT_SERIALIZER='json'
CELERY_ACCEPT_CONTENT=['json']
CELERY_TIMEZONE='Europe/Madrid'
CELERY_ENABLE_UTC=True
UPLOAD_FOLDER='ltwserver/uploads/'
VIRTUOSO_ODBC='DSN=VOS;UID=dba;PWD=dba;WideAsUTF16=Y'
MAX_MULTIPROCESSING=10
PAGINATION_PER_PAGE=20
SQLALCHEMY_DATABASE_URI='sqlite:///test.db'
COMMON_LABEL_PROPS=['http://www.w3.org/2000/01/rdf-schema#label', 'http://purl.org/dc/elements/1.1/name', 'http://xmlns.com/foaf/0.1/name', 'http://www.w3.org/2004/02/skos/core#prefLabel']
IMG_PROPS=['http://xmlns.com/foaf/0.1/depiction']
ANDROID_BIN='/home/jon/apps/android-sdk/tools/android'
LTW_ANDROID_LIB_PATH='/home/jon/virtualenvs/ltw/linked-tag-world/ltwandroidlib/'
BASE_APP_PATH='/home/jon/virtualenvs/ltw/linked-tag-world/ltwserver/ltwserver/android_app_base/'
NEW_APPS_PATH='/home/jon/newapps/'

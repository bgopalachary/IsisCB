NAME="isiscb"
DJANGODIR=/home/ec2-user/isiscb/isiscb/isiscb
SOCKFILE=/home/ec2-user/isiscb/run/gunicorn.sock
NUM_WORKERS=3
DJANGO_SETTINGS_MODULE=isiscb.settings
DJANGO_WSGI_MODULE=isiscb.wsgi

echo "Starting $NAME as `whoami`"

cd $DJANGODIR
workon isiscb

export DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE

RUNDIR=$(dirname $SOCKFILE)
test -d $RUNDIR || mkdir -p $RUNDIR

exec gunicorn ${DJANGO_WSGI_MODULE}:application \
  --name $NAME \
  --workers $NUM_WORKERS \
  --user=$USER --group=$GROUP \
  --bind=unix:$SOCKFILE \
  --log-level=debug \
  --log-file=-

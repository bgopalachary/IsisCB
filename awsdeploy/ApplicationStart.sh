cd /home/ec2-user/isiscb

# This is necessary for virtualenvwrapper (mkvirtualenv, workon) to work.
export WORKON_HOME=$HOME/.virtualenvs
source /usr/local/bin/virtualenvwrapper.sh

workon isiscb
touch /home/ec2-user/isiscb/isiscb/server_start
chmod 666 /home/ec2-user/isiscb/isiscb/server_start

awsdeploy/bin/set_environ.sh

# Supervisor manages gunicorn. See awsdeploy/supervisor.conf.
supervisorctl -c /etc/supervisor/conf.d/supervisor.conf start isiscb

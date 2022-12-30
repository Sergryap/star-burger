# #!/bin/bash
set -Eeuo pipefail
sudo apt update
sudo apt -y install git
sudo apt -y install postgresql
sudo apt -y install python3-pip
sudo apt -y install python3-venv
sudo apt -y install nginx
cd /
cd /opt/star_burger
sudo git pull
sudo ./node_modules/.bin/parcel build bundles-src/index.js --dist-dir bundles --public-url="./"
if ! [ -e venv ]
then
sudo python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn
if [ -e static ]
then
sudo rm -rf static
fi
python3 manage.py collectstatic --noinput
python3 manage.py migrate --noinput  
sudo systemctl daemon-reload
REVISION=$(git log -1 --pretty=format:'%H')
COMMIT_AUTHOR=$(git log -1 --pretty=format:'%an')
COMMIT_COMMENT=$(git log -1 --pretty=format:'%s')
curl \
-H "X-Rollbar-Access-Token: $ROLLBAR_SERVER_TOKEN" \
-H "Content-Type: application/json" \
-X POST 'https://api.rollbar.com/api/1/deploy' \
-d '{"environment": "home_pk", "revision": "'"$REVISION"'", "rollbar_name": "john", "local_username": "'"$COMMIT_AUTHOR"'", "comment": "'"$COMMIT_COMMENT"'", "status": "succeeded"}'
echo "Deploy completed successfully!"

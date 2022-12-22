# #!/bin/bash
set -Eeuo pipefail
sudo apt update
sudo apt -y install git
sudo apt -y install postgresql
sudo apt -y install python3-pip
sudo apt -y install python3-venv
sudo apt -y install nginx
curl -sL https://deb.nodesource.com/setup_16.x | sudo bash -
sudo apt -y install nodejs
cd /
cd /opt/star-burger
git pull
./node_modules/.bin/parcel build bundles-src/index.js --dist-dir bundles --public-url="./"
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn
if [ -e static ]
then
rm -rf static
fi
python3 manage.py collectstatic
python3 manage.py migrate
systemctl daemon-reload
REVISION=$(git log -1 --pretty=format:'%H')
COMMIT_AUTHOR=$(git log -1 --pretty=format:'%an')
COMMIT_COMMENT=$(git log -1 --pretty=format:'%s')
curl \
-H "X-Rollbar-Access-Token: $ROLLBAR_SERVER_TOKEN" \
-H "Content-Type: application/json" \
-X POST 'https://api.rollbar.com/api/1/deploy' \
-d '{"environment": "home_pk", "revision": "'"$REVISION"'", "rollbar_name": "john", "local_username": "'"$COMMIT_AUTHOR"'", "comment": "'"$COMMIT_COMMENT"'", "status": "succeeded"}'
echo "Successful data update!"

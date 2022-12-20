# #!/bin/bash
set -Eeuo pipefail
git pull
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
rm -rf static
python3 manage.py collectstatic
python3 manage.py migrate
systemctl daemon-reload
echo "Successful data update!"

python setup.py sdist
mkdir -p ~/rpmbuild/SOURCES
mv ./dist/* ~/rpmbuild/SOURCES
rmdir ./dist
rm -rf ./mojo_api.egg-info
rpmbuild -ba mojo_api.spec
sudo rpm -e mojo_api
sudo rpm -ivh ~/rpmbuild/RPMS/noarch/mojo_api-0.2-0.fc21.noarch.rpm

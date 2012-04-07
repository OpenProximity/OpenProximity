#!/bin/sh

set -e

if [ -z "${1}" ]; then
    echo "Usage ${0} <openproximity path>"
    exit 1
fi

URL="https://raw.github.com/OpenProximity/OpenProximity/master/"
RPATH="/opt/openproximity"
OPATH="${1}"

OPATH=$(echo ${OPATH} | sed -e 's/\//\\\//g')
RPATH=$(echo ${RPATH} | sed -e 's/\//\\\//g')

TDIR=$(mktemp -d)

pushd ${TDIR}

wget ${URL}/upstart/bluetoothd.conf
wget ${URL}/upstart/openproximity-web.conf
wget ${URL}/upstart/openproximity-rpc.conf
wget ${URL}/upstart/openproximity-rpc-scanner.conf
wget ${URL}/upstart/openproximity-rpc-uploader.conf
sed -i "s/${RPATH}/${OPATH}/g" openproximity-web.conf
sed -i "s/${RPATH}/${OPATH}/g" openproximity-rpc.conf
sed -i "s/${RPATH}/${OPATH}/g" openproximity-rpc-scanner.conf
sed -i "s/${RPATH}/${OPATH}/g" openproximity-rpc-uploader.conf

sudo cp *.conf /etc/init/
sudo mkdir -p /var/log/openproximity

popd

rm -rf ${TDIR}

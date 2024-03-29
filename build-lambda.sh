#!/bin/bash

set -e

if [[ ! -d $VIRTUAL_ENV ]] ; then
    echo "You must be in a VIRTUAL_ENV to build. See the README.md for instructions."
    exit 1
fi

echo "Backing up virtual env's current dependency list..."
pip freeze | grep -v "-e git" > env-dependencies.txt
echo "Clearing out the virtual env..."
pip uninstall -y -r env-dependencies.txt
echo "Installing prod dependencies only..."
pip install -r requirements.txt

VERSION=$(cat _version.py | grep "__version__" | awk -F '= "' '{print $2}' | awk -F '"' '{print $1}')
ZIP_DIR=$PWD
ZIP_NAME=slakkit-lambda-v$VERSION.zip
ZIP_FILE="$ZIP_DIR/$ZIP_NAME"

if [[ -f "$ZIP_FILE" ]]; then
    echo "Deleting old lambda zip file $ZIP_FILE..."
    rm -rf $ZIP_FILE
    echo "Deleted $ZIP_FILE"
fi

echo "Packaging the libraries..."
pushd $VIRTUAL_ENV/lib/python*/site-packages
zip -r9 $ZIP_FILE *
popd

echo "Adding the lambda soure code..."
source_files=`find . -name "*.py"`
zip -gR $ZIP_NAME $source_files
echo "Lambda deployment package created at $ZIP_FILE"

echo "Clearing out the virtual env..."
pip freeze | grep -v "-e git" | xargs pip uninstall -y
echo "Restoring virtual env dependencies from temp file..."
pip install -r env-dependencies.txt
echo "Removing temp dependencies file..."
rm -rf env-dependencies.txt

echo "Build finished, deplyment artefact $ZIP_FILE created"

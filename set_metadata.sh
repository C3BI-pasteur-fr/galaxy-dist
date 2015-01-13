#!/bin/sh

cd `dirname $0`
if test $(hostname) = "galaxytest.cluster.pasteur.fr"; then 
    qrsh -q galaxy -V -now n "/pasteur/projets/galaxytest/Pythons/Python_2.7.6/bin/python2.7 ./scripts/set_metadata.py $@"

else
    /pasteur/projets/galaxytest/Pythons/Python_2.7.6/bin/python2.7 ./scripts/set_metadata.py $@
fi

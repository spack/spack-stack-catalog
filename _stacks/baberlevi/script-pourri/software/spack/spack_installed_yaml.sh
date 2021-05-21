#!/bin/bash
for package in $(spack find -l | grep -v linux-rhel | xargs -n2 echo | tr ' ' ,)
do 
    hash=$(echo $package | cut -d ',' -f 1 | grep -i -e [0-9,a-z] ) 
    pkgname=$(echo $package | cut -d ',' -f 2 | cut -d '@' -f 1 | grep -i -e [0-9,a-z] ) 
    spack spec -y /$hash > $pkgname-$hash.yaml
done

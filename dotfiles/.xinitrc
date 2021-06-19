#!/bin/bash

mkdir -p ~/.local/share/keyrings
eval $(/usr/bin/gnome-keyring-daemon --start --components=gpg,pkcs11,secrets,ssh)
export $(gnome-keyring-daemon --start --components=pkcs11,secrets,ssh,gpg)
dbus-update-activation-environment --systemd DISPLAY

# [ -f "$HOME/.Xresources" ] && xrdb -merge "$HOME/.Xresources"


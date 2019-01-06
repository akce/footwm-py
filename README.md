# FootWM

FootWM: Focus On One Thing Window Manager.

## Dependencies

python3 and optionally a console (like xterm) for app/window menuing.

## Quick start

FootWM is written to be run inplace. Simply clone, add to your PATH and X startup file (eg, .xinitrc).

ie,

```
$ mkdir ~/opt
$ cd ~/opt
$ git clone https://github.com/akce/footwm.git
```

Add to *.xinitrc*

```
FOOTPATH=${HOME}/opt/footwm
export PYTHONPATH=${FOOTPATH}
export PATH=${FOOTPATH}/bin:${PATH}

# Footwm keyboard manager.
${FOOTPATH}/bin/footkeys start &
# Footwm app runner.
${FOOTPATH}/bin/footrun d start &

## Start the window manager.
${FOOTPATH}/bin/footwm
```

Customise configuration.
```
$ mkdir ~/.foot
$ cp -vi ~/opt/footwm/footwm/{footkeysconfig.py,appmenuconfig.py} ~/.foot
# Edit footkeysconfig.py and appmenuconfig.py as needed.
```

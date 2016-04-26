#! /bin/sh
#
# Test run the wm inside a Xephyr instance.
#

if [ -z "${DISPLAY}" ]; then
    xinit ./etc/xinitrc.test -- /usr/bin/X :4
else
    # Test is running inside of an X session, so fire up Xephyr.
    xinit ./etc/xinitrc.test -- /usr/bin/Xephyr :4 -ac -fullscreen -retro
fi

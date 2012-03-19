#include "Listener_WithLaunch.h"
#include <stdlib.h>
#include <sstream>
using namespace std;

static const char *_browser_list_prop[] = {
    "google-chrome",
    "firefox",
    0
};

static bool _has_cmd( const char *which, const char *exe ) {
    if ( which == 0 or exe == 0 )
        return false;
    string cmd = string( which ) + ' ' + exe;
    return system( cmd.c_str() ) == 0;
}


Listener_WithLaunch::Listener_WithLaunch( const char *port ) : Listener( port ), port( port ) {
    title = 0;
    launch = false;
    start_url = "";
    which_cmd = "which";
    xdotool_cmd = "xdotool";
    browser_list = _browser_list_prop;
}

void Listener_WithLaunch::rdy() {
    if ( launch ) {
        // try with xdotool
        if ( title and xdotool_cmd ) {
            string cmd = string( xdotool_cmd ) + " search " + title + "windowactivate key F5";
            if ( system( cmd.c_str() ) == 0 )
                return;
        }

        // else, try to launch in a new browser
        std::ostringstream cmd;
        for( int i = 0; browser_list[ i ]; ++i ) {
            if ( _has_cmd( which_cmd, browser_list[ i ] ) ) {
                string cmd = string( browser_list[ i ] ) + " http://localhost:" + port + start_url + " &";
                if ( system( cmd.c_str() ) == 0 )
                    return;
            }
        }
    }
}
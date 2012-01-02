#include "SocketHelp.h"
#include "EventLoop.h"
#include "Listener.h"

ListenerAncestor::ListenerAncestor( const char *port ) : EventObj( listening_socket( port ) ) {
}

bool ListenerAncestor::inp() {
    while ( true ) {
        int nd = accepting_socket( fd );
        if ( nd == -1 )
            break;
        *ev_loop << event_obj_factory( nd );
    }
    return false;
}

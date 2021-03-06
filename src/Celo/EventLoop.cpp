/*
 Copyright 2012 Structure Computation  www.structure-computation.com
 Copyright 2012 Hugo Leclerc

 This file is part of Celo.

 Celo is free software: you can redistribute it and/or modify
 it under the terms of the GNU Lesser General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 Celo is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU Lesser General Public License for more details.
 You should have received a copy of the GNU General Public License
 along with Celo. If not, see <http://www.gnu.org/licenses/>.
*/


#include "Util/StringHelp.h"
#include "Events/Event.h"
#include "EventLoop.h"

#include <sys/epoll.h>
#include <unistd.h>
#include <stdio.h>
#include <errno.h>

namespace Celo {

EventLoop::EventLoop() {
    // epoll init
    event_fd = epoll_create1( 0 );
    if ( event_fd < 0 )
        perror( "epoll_create1" );

    // default values
    last_ev_to_del = 0;
    ret = 0;
}

EventLoop::~EventLoop() {
    close( event_fd );
}

int EventLoop::run() {
    //
    cnt = true;

    // loop
    const int max_events = 64;
    epoll_event events[ max_events ];
    do {
        int nfds = epoll_wait( event_fd, events, max_events, -1 );
        if ( nfds == -1 ) {
            if ( errno != EINTR ) {
                perror( "epoll_wait" );
                return -1;
            }
            continue;
        }

        // for each event
        for( int n = 0; n < nfds; ++n ) {
            Events::Event *rq = reinterpret_cast<Events::Event *>( events[ n ].data.ptr );

            if ( events[ n ].events & EPOLLIN ) { // there are some input data
                rq->waiting &= ~Events::Event::WF_more_inp;
                rq->inp();
            }

            if ( events[ n ].events & EPOLLOUT ) { // ready for output (after a EAGAIN)
                rq->waiting &= ~Events::Event::WF_more_out;
                rq->out();
            }

            if ( events[ n ].events & EPOLLRDHUP ) { // end of the connection (gracefully closed by peer)
                rq->errors |= Events::Event::EF_rd_hup_error;
                rq->reg_for_deletion();
            }

            if ( events[ n ].events & EPOLLHUP ) { // end of the connection
                rq->errors |= Events::Event::EF_hup_error;
                rq->reg_for_deletion();
            }

            if ( events[ n ].events & EPOLLERR ) { // error
                rq->errors |= Events::Event::EF_generic_error;
                rq->reg_for_deletion();
            }

            // add to deletion list if nothing more to do
            if ( rq->waiting == 0 )
                rq->reg_for_deletion();
        }

        // deletions (due to closed connections, SSL errors, ...)
        if ( Events::Event *rq = last_ev_to_del ) {
            while ( true ) {
                Events::Event *oq = rq;
                rq = rq->next_ev_to_del;
                delete oq;
                if ( rq == oq )
                    break;
            }
            last_ev_to_del = 0;
        }
    } while ( cnt );

    return ret;
}

void EventLoop::stop( int ret_val ) {
    ret = ret_val;
    cnt = false;
}

EventLoop &EventLoop::operator<<( Events::Event *ev_obj ) {
    if ( not ev_obj or ev_obj->fd < 0 ) {
        delete ev_obj;
        return *this;
    }

    ev_obj->ev_loop = this;

    epoll_event ev;
    ev.events = EPOLLIN | EPOLLRDHUP | EPOLLET; // ET -> trigger
    ev.data.u64 = 0; // for valgrind on 32 bits machines
    ev.data.ptr = ev_obj;
    if ( epoll_ctl( event_fd, EPOLL_CTL_ADD, ev_obj->fd, &ev ) == -1 )
        perror( "epoll_ctl add" );

    ev_obj->rdy();
    return *this;
}

EventLoop &EventLoop::operator>>( Events::Event *ev_obj ) {
    if ( epoll_ctl( event_fd, EPOLL_CTL_DEL, ev_obj->fd, 0 ) == -1 )
        perror( "epoll_ctl del" );
    return *this;
}

void EventLoop::poll_out_obj( Events::Event *ev_obj ) {
    epoll_event ev;
    ev.events = EPOLLIN | EPOLLET | EPOLLRDHUP | EPOLLOUT;
    ev.data.u64 = 0; // for valgrind on 32 bits machines
    ev.data.ptr = ev_obj;
    if ( epoll_ctl( event_fd, EPOLL_CTL_MOD, ev_obj->fd, &ev ) == -1 )
        perror( "epoll_ctl mod (poll out)" );
}

}

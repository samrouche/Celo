#ifndef TIMER_H
#define TIMER_H

#include "EventObj.h"

/**
*/
class TimerAncestor : public EventObj {
public:
    TimerAncestor( double delay );
    virtual void inp();
    virtual bool end();

    virtual void timeout() = 0;
};


/**
*/
template<class ObjWithTimeout>
class Timer : public TimerAncestor {
public:
    Timer( ObjWithTimeout *obj, double delay ) : TimerAncestor( delay ), obj( obj ) {}
    virtual void timeout() { obj->timeout(); }

protected:
    ObjWithTimeout *obj;
};

#endif // TIMER_H

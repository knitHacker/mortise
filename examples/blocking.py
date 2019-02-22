#!/usr/bin/env python3

import queue
import random
import threading
import time

import mortise
from mortise import State


class Foo(State):
    def on_enter(self, st):
        self.count = 0

    def on_state(self, st):
        if st.msg:
            print("Foo: ", st.msg['data'])
            if st.msg['data'] == 'bar':
                return Bar
            elif st.msg['data'] == 'foo':
                self.count += 1
                print("Foos: {}".format(self.count))
                return True

    def on_leave(self, st):
        if st.msg and st.msg['data'] == 'foo':
            raise Exception("Called on_leave when shouldn't have")


class Bar(State):
    def on_enter(self, st):
        self.count = 0

    def on_state(self, st):
        if st.msg:
            print("Pong: ", st.msg['data'])
            if st.msg['data'] == 'foo':
                return Foo
            elif st.msg['data'] == 'bar':
                self.count += 1
                print("Bars: {}".format(self.count))
                return True

    def on_leave(self, st):
        if st.msg and st.msg['data'] == 'bar':
            raise Exception("Called on_leave when shouldn't have")


class ErrorState(State):
    def on_state(self, st):
        pass


def trap_msg(st):
    print("Trapped: {}".format(st.msg['data']))
    if st.msg['data'] != 'baz':
        raise Exception("Only trap 'baz' messages")


def loop(msg_queue):
    # msg_queue should be accessible to another thread which is
    # handling IPC traffic or otherwise generating events to be
    # consumed by the state machine

    fsm = mortise.StateMachine(
        initial_state=Foo,
        final_state=mortise.DefaultStates.End,
        default_error_state=ErrorState,
        msg_queue=msg_queue,
        log_fn=print,
        trap_fn=trap_msg)

    # Initial kick of the state machine for setup
    fsm.tick()

    while True:
        fsm.tick(msg_queue.get())


def msg_loop(msg_queue):
    # NOTE: The messages consumed by Mortise are content agnostic, the
    # implementation / checking of message type is up to the user.

    idx = 0
    while True:
        messages = ['foo', 'bar', 'baz']
        idx = random.randint(0, 2)
        idx %= len(messages)
        msg_queue.put({'data': messages[idx]})
        time.sleep(1)


def main():
    msg_queue = queue.Queue()
    mortise_t = threading.Thread(target=loop, kwargs={'msg_queue': msg_queue})
    msg_t = threading.Thread(target=msg_loop, kwargs={'msg_queue': msg_queue})

    mortise_t.daemon = True
    msg_t.daemon = True

    mortise_t.start()
    msg_t.start()

    mortise_t.join()
    msg_t.join()

main()

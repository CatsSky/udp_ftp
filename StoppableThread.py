import threading

class StoppableThread(threading.Thread):

    def __init__(self,  *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self.stopEvent = threading.Event()

    def stop(self):
        self.stopEvent.set()

    def stopped(self):
        return self.stopEvent.is_set()

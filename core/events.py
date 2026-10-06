import queue
from core.models import TaskEvent


class EventBus:
    def __init__(self):
        self._queue: queue.Queue[TaskEvent] = queue.Queue()

    def emit(self, event: TaskEvent):
        self._queue.put(event)

    def get_event(self) -> TaskEvent:
        return self._queue.get_nowait()

    def empty(self) -> bool:
        return self._queue.empty()
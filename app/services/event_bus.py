import asyncio
from collections import defaultdict, deque
from collections.abc import AsyncIterator

from app.models.events import ScanEvent


class EventBus:
    def __init__(self, history_size: int = 200) -> None:
        self._history_size = history_size
        self._history: dict[str, deque[ScanEvent]] = defaultdict(lambda: deque(maxlen=history_size))
        self._subscribers: dict[str, set[asyncio.Queue[ScanEvent]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def publish(self, event: ScanEvent) -> None:
        async with self._lock:
            self._history[event.scan_id].append(event)
            subscribers = list(self._subscribers.get(event.scan_id, set()))

        for queue in subscribers:
            await queue.put(event)

    async def subscribe(self, scan_id: str) -> AsyncIterator[ScanEvent]:
        queue: asyncio.Queue[ScanEvent] = asyncio.Queue(maxsize=self._history_size)
        async with self._lock:
            for event in self._history.get(scan_id, []):
                await queue.put(event)
            self._subscribers[scan_id].add(queue)

        try:
            while True:
                event = await queue.get()
                yield event
                if event.type in {"completed", "error"}:
                    break
        finally:
            async with self._lock:
                self._subscribers.get(scan_id, set()).discard(queue)


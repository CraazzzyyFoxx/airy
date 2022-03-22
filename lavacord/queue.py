"""
MIT License

Copyright (c) 2019-2021 PythonistaGuild
Copyright (c) 2022-present CrazzzyyFoxx

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


from __future__ import annotations

from collections import deque
from datetime import timedelta
from copy import copy
from typing import (
    Generic,
    Iterable,
    Iterator,
    List,
    Optional,
    Type,
    TypeVar,
    Union
)


from . import abc, exceptions
from .types.queue import Queue as QueueBase
from .enums import RepeatMode

__all__ = (
    "BaseQueue",
    "Queue"
)


QT = TypeVar("QT", bound=QueueBase)


class BaseQueue(Iterable[abc.Track], Generic[QT]):
    """Basic Queue implementation for Playable objects.

    .. warning::
        This Queue class only accepts Playable objects. E.g YouTubeTrack, SoundCloudTrack.

    Parameters
    ----------
    max_size: Optional[int]
        The maximum allowed tracks in the Queue. If None, no maximum is used. Defaults to None.
    """

    __slots__ = ("max_size", "_queue", "_overflow")

    def __init__(
        self,
        max_size: Optional[int] = None,
        *,
        overflow: bool = True,
        queue_cls: Type[QT] = deque,
    ):
        self.max_size: Optional[int] = max_size
        self._queue: QT = queue_cls()  # type: ignore
        self._overflow: bool = overflow

    def __str__(self) -> str:
        """String showing all Playable objects appearing as a list."""
        return str(list(f"{t}" for t in self))

    def __repr__(self) -> str:
        """Official representation with max_size and member count."""
        return (
            f"<{self.__class__.__name__} max_size={self.max_size} members={self.count}>"
        )

    def __bool__(self) -> bool:
        """Treats the queue as a bool, with it evaluating True when it contains members."""
        return bool(self.count)

    def __call__(self, item: abc.Track) -> None:
        """Allows the queue instance to be called directly in order to add a member."""
        self.put(item)

    def __len__(self) -> int:
        """Return the number of members in the queue."""
        return self.count

    def __getitem__(self, index: int) -> abc.Track:
        """Returns a member at the given position.

        Does not remove item from queue.
        """
        if not isinstance(index, int):
            raise ValueError("'int' type required.'")

        return self._queue[index]

    def __setitem__(self, index: int, item: abc.Track):
        """Inserts an item at given position."""
        if not isinstance(index, int):
            raise ValueError("'int' type required.'")

        self.put_at_index(index, item)

    def __delitem__(self, index: int) -> None:
        """Delete item at given position."""
        self._queue.__delitem__(index)

    def __iter__(self) -> Iterator[abc.Track]:
        """Iterate over members in the queue.

        Does not remove items when iterating.
        """
        return self._queue.__iter__()

    def __reversed__(self) -> Iterator[abc.Track]:
        """Iterate over members in reverse order."""
        return self._queue.__reversed__()

    def __contains__(self, item: abc.Track) -> bool:
        """Check if an item is a member of the queue."""
        return item in self._queue

    def __add__(self, other: Iterable[abc.Track]) -> BaseQueue[QT]:
        """Return a new queue containing all members.

        The new queue will have the same max_size as the original.
        """
        if not isinstance(other, Iterable):
            raise TypeError(f"Adding with the '{type(other)}' type is not supported.")

        new_queue = self.copy()
        new_queue.extend(other)
        return new_queue

    def __iadd__(self, other: Union[Iterable[abc.Track], abc.Track]) -> BaseQueue:
        """Add items to queue."""
        if isinstance(other, abc.Track):
            self.put(other)
            return self

        if isinstance(other, Iterable):
            self.extend(other)
            return self

        raise TypeError(f"Adding '{type(other)}' type to the queue is not supported.")

    def _get(self) -> abc.Track:
        return self._queue.popleft()

    def _drop(self) -> abc.Track:
        return self._queue.pop()

    def _index(self, item: abc.Track) -> int:
        return self._queue.index(item)

    def _put(self, item: abc.Track) -> None:
        self._queue.append(item)

    def _insert(self, index: int, item: abc.Track) -> None:
        self._queue.insert(index, item)

    @staticmethod
    def _check_playable(item: abc.Track) -> abc.Track:
        if not isinstance(item, abc.Track):
            raise TypeError("Only Playable objects are supported.")

        return item

    @classmethod
    def _check_playable_container(cls, iterable: Iterable) -> List[abc.Track]:
        iterable = list(iterable)
        for item in iterable:
            cls._check_playable(item)

        return iterable

    @property
    def count(self) -> int:
        """Returns queue member count."""
        return len(self._queue)

    @property
    def is_empty(self) -> bool:
        """Returns True if queue has no members."""
        return not bool(self.count)

    @property
    def is_full(self) -> bool:
        """Returns True if queue item count has reached max_size."""
        return False if self.max_size is None else self.count >= self.max_size

    def get(self) -> abc.Track:
        """Return next immediately available item in queue if any.

        Raises QueueEmpty if no items in queue.
        """
        if self.is_empty:
            raise exceptions.QueueEmpty("No items in the queue.")

        return self._get()

    def pop(self) -> abc.Track:
        """Return item from the right end side of the queue.

        Raises QueueEmpty if no items in queue.
        """
        if self.is_empty:
            raise exceptions.QueueEmpty("No items in the queue.")

        return self._queue.pop()

    def find_position(self, item: abc.Track) -> int:
        """Find the position a given item within the queue.

        Raises ValueError if item is not in queue.
        """
        return self._index(self._check_playable(item))

    def put(self, item: abc.Track) -> None:
        """Put the given item into the back of the queue."""
        if self.is_full:
            if not self._overflow:
                raise exceptions.QueueFull(f"Queue max_size of {self.max_size} has been reached.")

            self._drop()

        return self._put(self._check_playable(item))

    def put_at_index(self, index: int, item: abc.Track) -> None:
        """Put the given item into the queue at the specified index."""
        if self.is_full:
            if not self._overflow:
                raise exceptions.QueueFull(f"Queue max_size of {self.max_size} has been reached.")

            self._drop()

        return self._insert(index, self._check_playable(item))

    def put_at_front(self, item: abc.Track) -> None:
        """Put the given item into the front of the queue."""
        return self.put_at_index(0, item)

    def extend(self, iterable: Iterable[abc.Track], *, atomic: bool = True) -> None:
        """
        Add the members of the given iterable to the end of the queue.

        If atomic is set to True, no tracks will be added upon any exceptions.

        If atomic is set to False, as many tracks will be added as possible.

        When overflow is enabled for the queue, `atomic=True` won't prevent dropped items.
        """
        if atomic:
            iterable = self._check_playable_container(iterable)

            if not self._overflow and self.max_size is not None:
                new_len = len(iterable)

                if (new_len + self.count) > self.max_size:
                    raise exceptions.QueueFull(
                        f"Queue has {self.count}/{self.max_size} items, "
                        f"cannot add {new_len} more."
                    )

        for item in iterable:
            self.put(item)

    def copy(self) -> BaseQueue:
        """Create a copy of the current queue including it's members."""
        new_queue = self.__class__(max_size=self.max_size)
        new_queue._queue = copy(self._queue)

        return new_queue

    def clear(self) -> None:
        """Remove all items from the queue."""
        self._queue.clear()


class Queue(BaseQueue):
    __slots__ = ("_history", "_repeat_mode")

    def __init__(
            self,
            max_size: Optional[int] = 100,
            history_max_size: Optional[int] = 100
    ):
        super().__init__(max_size, overflow=False)
        self._history = BaseQueue(history_max_size)

        self._repeat_mode = RepeatMode.OFF

    def __str__(self) -> List[str]:
        """String showing all Playable objects appearing as a list."""
        return [f"{track}" for track in self._queue]

    @property
    def upcoming(self) -> BaseQueue[abc.Track]:
        return self._queue

    @property
    def history(self) -> BaseQueue[abc.Track]:
        return self._history

    @property
    def current_track(self):
        if not self.history:
            return
        return self.history[0]

    @property
    def current_index(self):
        return len(self.history)

    @property
    def repeat_mode(self):
        return self._repeat_mode

    def clear(self):
        self._history.clear()
        self.clear()

    def _get(self) -> abc.Track:
        item = super()._get()
        self._history.put_at_front(item)
        return item

    def get_next_track(self) -> Union[abc.Track, abc.Track]:
        if self._repeat_mode == RepeatMode.ONE:
            return self.current_track

        elif self._repeat_mode == RepeatMode.ALL and self.is_empty:
            self._history.put_at_front(self.current_track)
            self._queue = self._history._queue.copy()
            self._history.clear()
            return self._get()

        return self._get()

    def get_previous_track(self):
        if len(self._history) < 1:
            raise exceptions.QueueHistoryEmpty

        self.put_at_front(self._history.get())
        self.put_at_index(1, self.current_track)

    def skip_to_index(self, index: int):
        if self.current_index == index:
            return

        if index < 0:
            index = -index

        if self.current_index < index:
            while self.current_index < index:
                self.get()
        else:
            while self.current_index >= index:
                self.put_at_front(self._history.get())

        return self._get()

    def set_repeat_mode(self, mode: str):
        self._repeat_mode = RepeatMode(mode)

    def estimated_duration(self, position: Union[int, float]):
        current_track = self.current_track

        if not current_track:
            return '0:00:00'
        if current_track.isStream:
            return 'Infinity'

        estimated_time = current_track.length
        estimated_time -= position

        if self.upcoming is None:
            return timedelta(seconds=int(estimated_time / 1000))

        for track in self.upcoming:
            if track.isStream:
                return 'Infinity'
            estimated_time += track.length

        return timedelta(seconds=int(estimated_time / 1000))

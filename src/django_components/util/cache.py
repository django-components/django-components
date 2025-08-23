from collections.abc import Hashable
from typing import Dict, Generic, Optional, TypeVar, cast

T = TypeVar("T")


class CacheNode(Generic[T]):
    """A node in the doubly linked list."""

    def __init__(self, key: Hashable, value: T) -> None:
        self.key = key
        self.value = value
        self.prev: Optional[CacheNode] = None
        self.next: Optional[CacheNode] = None


class LRUCache(Generic[T]):
    """A simple LRU Cache implementation."""

    def __init__(self, maxsize: Optional[int] = None) -> None:
        """
        Initialize the LRU cache.

        :param maxsize: Maximum number of items the cache can hold. If None, the cache is unbounded.
        """
        self.maxsize = maxsize
        self.cache: Dict[Hashable, CacheNode[T]] = {}  # Maps keys to nodes in the doubly linked list
        # Dummy head and tail nodes to simplify operations
        self.head = CacheNode[T]("", cast("T", None))  # Most recently used
        self.tail = CacheNode[T]("", cast("T", None))  # Least recently used
        self.head.next = self.tail
        self.tail.prev = self.head

    def get(self, key: Hashable) -> Optional[T]:
        """
        Retrieve the value associated with the key.

        :param key: Key to look up in the cache.
        :return: Value associated with the key, or None if not found.
        """
        if key in self.cache:
            node = self.cache[key]
            # Move the accessed node to the front (most recently used)
            self._remove(node)
            self._add_to_front(node)
            return node.value

        return None  # Key not found

    def has(self, key: Hashable) -> bool:
        """
        Check if the key is in the cache.

        :param key: Key to check.
        :return: True if the key is in the cache, False otherwise.
        """
        return key in self.cache

    def set(self, key: Hashable, value: T) -> None:
        """
        Insert or update the value associated with the key.

        :param key: Key to insert or update.
        :param value: Value to associate with the key.
        """
        # Noop if maxsize is set to 0
        if self.maxsize is not None and self.maxsize <= 0:
            return

        if key in self.cache:
            node = self.cache[key]
            # Update the value
            node.value = value
            # Move the node to the front (most recently used)
            self._remove(node)
            self._add_to_front(node)
        else:
            if self.maxsize is not None and len(self.cache) >= self.maxsize:
                # Cache is full; remove the least recently used item
                lru_node = self.tail.prev
                if lru_node is None:
                    raise RuntimeError("LRUCache: Tail node is None")
                self._remove(lru_node)
                del self.cache[lru_node.key]

            # Add the new node to the front
            new_node = CacheNode[T](key, value)
            self.cache[key] = new_node
            self._add_to_front(new_node)

    def clear(self) -> None:
        """Clear the cache."""
        self.cache.clear()
        self.head.next = self.tail
        self.tail.prev = self.head

    def _remove(self, node: CacheNode) -> None:
        """Remove a node from the doubly linked list."""
        prev_node = node.prev
        next_node = node.next

        if prev_node is not None:
            prev_node.next = next_node

        if next_node is not None:
            next_node.prev = prev_node

    def _add_to_front(self, node: CacheNode) -> None:
        """Add a node right after the head (mark it as most recently used)."""
        node.next = self.head.next
        node.prev = self.head

        if self.head.next:
            self.head.next.prev = node
            self.head.next = node

"""C++-inspired memory pool and object pooling optimization for 3D CAD operations."""

from __future__ import annotations

import gc
import logging
import threading
import time
import weakref
from array import array
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Type, TypeVar, Generic
from contextlib import contextmanager

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


T = TypeVar('T')


class MemoryAlignment(Enum):
    """Memory alignment options (C++ alignment equivalent)."""
    BYTE = 1
    WORD = 4      # 32-bit
    DWORD = 8     # 64-bit
    CACHE_LINE = 64  # Typical cache line size
    PAGE = 4096   # Memory page size


class PoolStrategy(Enum):
    """Memory pool allocation strategies."""
    FIRST_FIT = "first_fit"      # C++ std::allocator style
    BEST_FIT = "best_fit"        # Optimal fit
    WORST_FIT = "worst_fit"      # For fragmentation reduction
    BUDDY_SYSTEM = "buddy"       # Binary buddy system
    SLAB = "slab"                # Linux slab allocator style


@dataclass
class MemoryBlock:
    """C++-style memory block with metadata."""
    address: int
    size: int
    is_free: bool = True
    alignment: int = 8
    pool_type: str = "general"
    allocated_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    reference_count: int = 0


@dataclass
class PoolStatistics:
    """Memory pool statistics (C++ profiling equivalent)."""
    total_allocated: int = 0
    total_free: int = 0
    fragmentation_ratio: float = 0.0
    allocation_count: int = 0
    deallocation_count: int = 0
    peak_usage: int = 0
    current_usage: int = 0
    pool_efficiency: float = 0.0


class CppStyleMemoryPool:
    """C++ std::pmr::memory_resource inspired memory pool."""

    def __init__(self, initial_size: int = 1024 * 1024,  # 1MB
                 alignment: MemoryAlignment = MemoryAlignment.CACHE_LINE,
                 strategy: PoolStrategy = PoolStrategy.BUDDY_SYSTEM):
        self.logger = logging.getLogger(__name__)
        self.initial_size = initial_size
        self.alignment = alignment.value
        self.strategy = strategy
        self.pool_size = initial_size
        self.allocated_blocks: List[MemoryBlock] = []
        self.free_blocks: List[MemoryBlock] = []
        self.memory_map: Dict[int, MemoryBlock] = {}
        self._lock = threading.RLock()
        self.statistics = PoolStatistics()

        # Initialize pool
        self._initialize_pool()

    def _initialize_pool(self) -> None:
        """Initialize memory pool (C++ constructor equivalent)."""
        # Create initial free block
        initial_block = MemoryBlock(
            address=0,
            size=self.pool_size,
            is_free=True,
            alignment=self.alignment,
            pool_type="initial"
        )

        self.free_blocks.append(initial_block)
        self.memory_map[0] = initial_block

    def allocate(self, size: int, alignment: Optional[int] = None) -> Optional[int]:
        """Allocate memory (C++ new equivalent)."""
        if alignment is None:
            alignment = self.alignment

        # Align size to alignment boundary
        aligned_size = self._align_size(size, alignment)

        with self._lock:
            # Find suitable free block based on strategy
            block = self._find_free_block(aligned_size)

            if block is None:
                # Pool expansion needed (C++ reallocation)
                return None

            # Split block if necessary
            remaining_size = block.size - aligned_size
            if remaining_size > 0:
                self._split_block(block, aligned_size)

            # Mark block as allocated
            block.is_free = False
            block.reference_count = 1
            self.statistics.allocation_count += 1
            self.statistics.total_allocated += aligned_size
            self.statistics.current_usage += aligned_size
            self.statistics.peak_usage = max(self.statistics.peak_usage, self.statistics.current_usage)

            self.logger.debug(f"Allocated {aligned_size} bytes at address {block.address}")
            return block.address

    def deallocate(self, address: int) -> bool:
        """Deallocate memory (C++ delete equivalent)."""
        with self._lock:
            if address not in self.memory_map:
                self.logger.warning(f"Attempted to deallocate invalid address: {address}")
                return False

            block = self.memory_map[address]

            if block.is_free:
                self.logger.warning(f"Double free detected at address: {address}")
                return False

            # Mark as free
            block.is_free = True
            block.reference_count = 0
            self.statistics.deallocation_count += 1
            self.statistics.total_free += block.size
            self.statistics.current_usage -= block.size

            # Try to coalesce adjacent free blocks (C++ defragmentation)
            self._coalesce_free_blocks()

            self.logger.debug(f"Deallocated {block.size} bytes at address {address}")
            return True

    def _find_free_block(self, size: int) -> Optional[MemoryBlock]:
        """Find free block using allocation strategy."""
        if self.strategy == PoolStrategy.FIRST_FIT:
            return self._first_fit(size)
        elif self.strategy == PoolStrategy.BEST_FIT:
            return self._best_fit(size)
        elif self.strategy == PoolStrategy.BUDDY_SYSTEM:
            return self._buddy_allocate(size)
        else:
            return self._first_fit(size)  # Default

    def _first_fit(self, size: int) -> Optional[MemoryBlock]:
        """First-fit allocation strategy."""
        for block in self.free_blocks:
            if block.size >= size:
                return block
        return None

    def _best_fit(self, size: int) -> Optional[MemoryBlock]:
        """Best-fit allocation strategy."""
        best_block = None
        best_size = float('inf')

        for block in self.free_blocks:
            if block.size >= size and block.size < best_size:
                best_size = block.size
                best_block = block

        return best_block

    def _buddy_allocate(self, size: int) -> Optional[MemoryBlock]:
        """Binary buddy system allocation."""
        # Find power-of-two size that can contain requested size
        target_size = 1
        while target_size < size:
            target_size *= 2

        # Find buddy block of exact size
        for block in self.free_blocks:
            if block.size == target_size:
                return block

        # Split larger block if available
        for block in self.free_blocks:
            if block.size > target_size:
                return self._split_to_buddy_size(block, target_size)

        return None

    def _split_to_buddy_size(self, block: MemoryBlock, target_size: int) -> Optional[MemoryBlock]:
        """Split block to buddy size."""
        while block.size > target_size and block.size >= target_size * 2:
            half_size = block.size // 2

            # Create two buddy blocks
            buddy1 = MemoryBlock(
                address=block.address,
                size=half_size,
                is_free=True,
                alignment=self.alignment,
                pool_type="buddy"
            )

            buddy2 = MemoryBlock(
                address=block.address + half_size,
                size=half_size,
                is_free=True,
                alignment=self.alignment,
                pool_type="buddy"
            )

            # Replace original block
            self.free_blocks.remove(block)
            self.free_blocks.extend([buddy1, buddy2])
            self.memory_map[block.address] = buddy1
            self.memory_map[block.address + half_size] = buddy2

            block = buddy1

        return block if block.size == target_size else None

    def _split_block(self, block: MemoryBlock, size: int) -> None:
        """Split memory block."""
        if block.size <= size:
            return

        # Create remaining block
        remaining_block = MemoryBlock(
            address=block.address + size,
            size=block.size - size,
            is_free=True,
            alignment=self.alignment,
            pool_type=block.pool_type
        )

        # Update original block
        block.size = size

        # Add remaining block to free list
        self.free_blocks.append(remaining_block)
        self.memory_map[remaining_block.address] = remaining_block

    def _coalesce_free_blocks(self) -> None:
        """Coalesce adjacent free blocks (C++ defragmentation)."""
        # Sort free blocks by address
        self.free_blocks.sort(key=lambda b: b.address)

        i = 0
        while i < len(self.free_blocks) - 1:
            current = self.free_blocks[i]
            next_block = self.free_blocks[i + 1]

            # Check if adjacent
            if current.address + current.size == next_block.address:
                # Merge blocks
                merged_block = MemoryBlock(
                    address=current.address,
                    size=current.size + next_block.size,
                    is_free=True,
                    alignment=self.alignment,
                    pool_type="merged"
                )

                # Remove original blocks
                self.free_blocks.pop(i + 1)
                self.free_blocks.pop(i)

                # Update memory map
                del self.memory_map[current.address]
                del self.memory_map[next_block.address]
                self.memory_map[merged_block.address] = merged_block

                # Add merged block
                self.free_blocks.insert(i, merged_block)

                # Check again from same position
                continue

            i += 1

    def _align_size(self, size: int, alignment: int) -> int:
        """Align size to alignment boundary."""
        return (size + alignment - 1) & ~(alignment - 1)

    def get_statistics(self) -> PoolStatistics:
        """Get pool statistics (C++ profiling equivalent)."""
        with self._lock:
            # Calculate fragmentation
            total_free = sum(block.size for block in self.free_blocks)
            total_allocated = self.statistics.total_allocated

            if total_allocated + total_free > 0:
                self.statistics.fragmentation_ratio = total_free / (total_allocated + total_free)

            # Calculate efficiency
            if self.statistics.allocation_count > 0:
                self.statistics.pool_efficiency = self.statistics.deallocation_count / self.statistics.allocation_count

            return self.statistics


class ObjectPool(Generic[T]):
    """C++-style object pool for reusable objects."""

    def __init__(self, factory_func: Callable[[], T],
                 initial_size: int = 10,
                 max_size: int = 100,
                 reset_func: Optional[Callable[[T], None]] = None):
        self.logger = logging.getLogger(__name__)
        self.factory_func = factory_func
        self.reset_func = reset_func
        self.initial_size = initial_size
        self.max_size = max_size
        self.pool: List[T] = []
        self.in_use: Set[T] = set()
        self.created_count = 0
        self.reused_count = 0
        self._lock = threading.Lock()

        # Initialize pool
        self._initialize_pool()

    def _initialize_pool(self) -> None:
        """Initialize object pool."""
        for _ in range(self.initial_size):
            try:
                obj = self.factory_func()
                self.pool.append(obj)
                self.created_count += 1
            except Exception as e:
                self.logger.error(f"Failed to create pooled object: {e}")
                break

    def acquire(self) -> T:
        """Acquire object from pool (C++ RAII equivalent)."""
        with self._lock:
            # Try to get from pool first
            if self.pool:
                obj = self.pool.pop()
                self.in_use.add(obj)
                self.reused_count += 1
                return obj

            # Create new object
            try:
                obj = self.factory_func()
                self.in_use.add(obj)
                self.created_count += 1

                # Check pool size limits
                if len(self.in_use) > self.max_size:
                    self.logger.warning("Object pool size limit exceeded")

                return obj

            except Exception as e:
                self.logger.error(f"Failed to create object: {e}")
                raise

    def release(self, obj: T) -> None:
        """Release object back to pool (C++ destructor equivalent)."""
        with self._lock:
            if obj not in self.in_use:
                self.logger.warning(f"Attempted to release object not in use: {obj}")
                return

            # Reset object if reset function provided
            if self.reset_func:
                try:
                    self.reset_func(obj)
                except Exception as e:
                    self.logger.error(f"Failed to reset object: {e}")

            # Return to pool if not full
            if len(self.pool) < self.max_size:
                self.pool.append(obj)
                self.in_use.remove(obj)
            else:
                # Pool full, discard object
                self.in_use.remove(obj)

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        with self._lock:
            return {
                "pool_size": len(self.pool),
                "in_use_count": len(self.in_use),
                "created_count": self.created_count,
                "reused_count": self.reused_count,
                "reuse_ratio": self.reused_count / max(self.created_count, 1),
                "max_size": self.max_size
            }

    @contextmanager
    def acquire_context(self) -> T:
        """Context manager for object acquisition (C++ RAII)."""
        obj = self.acquire()
        try:
            yield obj
        finally:
            self.release(obj)


class STLProcessingPool:
    """Specialized pool for STL processing objects."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Create object pools for STL processing
        self.vertex_pools = self._create_vertex_pools()
        self.face_pools = self._create_face_pools()
        self.buffer_pools = self._create_buffer_pools()

    def _create_vertex_pools(self) -> Dict[str, ObjectPool]:
        """Create vertex-related object pools."""
        pools = {}

        # Pool for vertex arrays
        def create_vertex_array():
            if HAS_NUMPY:
                return np.zeros((1000, 3), dtype=np.float32)
            else:
                return [[0.0, 0.0, 0.0] for _ in range(1000)]

        def reset_vertex_array(arr):
            if HAS_NUMPY:
                arr.fill(0.0)
            else:
                for vertex in arr:
                    vertex[0] = vertex[1] = vertex[2] = 0.0

        pools["vertex_array"] = ObjectPool(
            factory_func=create_vertex_array,
            initial_size=5,
            max_size=20,
            reset_func=reset_vertex_array
        )

        return pools

    def _create_face_pools(self) -> Dict[str, ObjectPool]:
        """Create face-related object pools."""
        pools = {}

        # Pool for face index arrays
        def create_face_array():
            if HAS_NUMPY:
                return np.zeros((1000, 3), dtype=np.uint32)
            else:
                return [[0, 0, 0] for _ in range(1000)]

        def reset_face_array(arr):
            if HAS_NUMPY:
                arr.fill(0)
            else:
                for face in arr:
                    face[0] = face[1] = face[2] = 0

        pools["face_array"] = ObjectPool(
            factory_func=create_face_array,
            initial_size=5,
            max_size=20,
            reset_func=reset_face_array
        )

        return pools

    def _create_buffer_pools(self) -> Dict[str, ObjectPool]:
        """Create buffer object pools."""
        pools = {}

        # Pool for binary data buffers
        def create_buffer():
            return bytearray(8192)  # 8KB buffer

        def reset_buffer(buf):
            buf[:] = b'\x00' * len(buf)

        pools["binary_buffer"] = ObjectPool(
            factory_func=create_buffer,
            initial_size=10,
            max_size=50,
            reset_func=reset_buffer
        )

        return pools

    def get_vertex_array(self) -> Any:
        """Get vertex array from pool."""
        return self.vertex_pools["vertex_array"].acquire()

    def return_vertex_array(self, array: Any) -> None:
        """Return vertex array to pool."""
        self.vertex_pools["vertex_array"].release(array)

    def get_face_array(self) -> Any:
        """Get face array from pool."""
        return self.face_pools["face_array"].acquire()

    def return_face_array(self, array: Any) -> None:
        """Return face array to pool."""
        self.face_pools["face_array"].release(array)

    def get_buffer(self) -> bytearray:
        """Get buffer from pool."""
        return self.buffer_pools["binary_buffer"].acquire()

    def return_buffer(self, buffer: bytearray) -> None:
        """Return buffer to pool."""
        self.buffer_pools["binary_buffer"].release(buffer)

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all pools."""
        return {
            "vertex_pools": {name: pool.get_stats() for name, pool in self.vertex_pools.items()},
            "face_pools": {name: pool.get_stats() for name, pool in self.face_pools.items()},
            "buffer_pools": {name: pool.get_stats() for name, pool in self.buffer_pools.items()}
        }


class MemoryArena:
    """C++-style memory arena for contiguous allocations."""

    def __init__(self, size: int = 1024 * 1024):  # 1MB default
        self.logger = logging.getLogger(__name__)
        self.size = size
        self.arena_start = 0  # Would be actual memory address in C++
        self.allocated_offset = 0
        self.free_list: List[Tuple[int, int]] = []  # (offset, size) pairs
        self._lock = threading.Lock()

    def allocate(self, size: int, alignment: int = 8) -> Optional[int]:
        """Allocate memory in arena (C++ arena allocation)."""
        with self._lock:
            # Align size
            aligned_size = (size + alignment - 1) & ~(alignment - 1)

            # Check if arena has enough space
            if self.allocated_offset + aligned_size > self.size:
                self.logger.warning(f"Arena allocation failed: {aligned_size} bytes requested, "
                                  f"{self.size - self.allocated_offset} bytes available")
                return None

            # Allocate at current offset
            offset = self.allocated_offset
            self.allocated_offset += aligned_size

            self.logger.debug(f"Arena allocated {aligned_size} bytes at offset {offset}")
            return offset

    def reset(self) -> None:
        """Reset arena (C++ arena reset)."""
        with self._lock:
            self.allocated_offset = 0
            self.free_list.clear()
            self.logger.debug("Arena reset")

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get arena usage statistics."""
        with self._lock:
            return {
                "total_size": self.size,
                "allocated": self.allocated_offset,
                "available": self.size - self.allocated_offset,
                "utilization_ratio": self.allocated_offset / self.size if self.size > 0 else 0.0
            }


class ReferenceCountingManager:
    """C++ std::shared_ptr style reference counting."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.ref_counts: Dict[int, int] = {}
        self.weak_refs: Dict[int, weakref.ReferenceType] = {}
        self._lock = threading.Lock()

    def add_reference(self, obj_id: int, obj: Any) -> None:
        """Add reference (C++ shared_ptr constructor)."""
        with self._lock:
            self.ref_counts[obj_id] = self.ref_counts.get(obj_id, 0) + 1

            # Create weak reference for cleanup
            self.weak_refs[obj_id] = weakref.ref(obj, lambda ref: self._cleanup_object(obj_id))

    def remove_reference(self, obj_id: int) -> bool:
        """Remove reference (C++ shared_ptr destructor)."""
        with self._lock:
            if obj_id not in self.ref_counts:
                return False

            self.ref_counts[obj_id] -= 1

            if self.ref_counts[obj_id] <= 0:
                # Object can be destroyed
                self._destroy_object(obj_id)
                return True

            return False

    def get_reference_count(self, obj_id: int) -> int:
        """Get reference count (C++ use_count equivalent)."""
        with self._lock:
            return self.ref_counts.get(obj_id, 0)

    def _cleanup_object(self, obj_id: int) -> None:
        """Cleanup object when reference count reaches zero."""
        with self._lock:
            if obj_id in self.ref_counts:
                del self.ref_counts[obj_id]
            if obj_id in self.weak_refs:
                del self.weak_refs[obj_id]

        self.logger.debug(f"Cleaned up object {obj_id}")

    def _destroy_object(self, obj_id: int) -> None:
        """Destroy object."""
        self._cleanup_object(obj_id)
        self.logger.debug(f"Destroyed object {obj_id}")


class OptimizedMeshBuffer:
    """Optimized mesh buffer with C++-style memory layout."""

    def __init__(self, vertex_count: int = 0, face_count: int = 0):
        self.logger = logging.getLogger(__name__)
        self.vertex_count = vertex_count
        self.face_count = face_count
        self.vertex_buffer: Optional[array] = None
        self.face_buffer: Optional[array] = None
        self.normal_buffer: Optional[array] = None
        self.uv_buffer: Optional[array] = None

        # C++-style memory layout optimization
        self._optimize_memory_layout()

    def _optimize_memory_layout(self) -> None:
        """Optimize memory layout for cache efficiency (C++ struct packing)."""
        if self.vertex_count > 0:
            # Interleaved vertex data: position (3), normal (3), uv (2) = 8 floats per vertex
            self.vertex_buffer = array('f', [0.0] * (self.vertex_count * 8))

        if self.face_count > 0:
            # Face indices: 3 indices per face
            self.face_buffer = array('I', [0] * (self.face_count * 3))

    def set_vertex_data(self, vertex_index: int, position: List[float],
                       normal: Optional[List[float]] = None, uv: Optional[List[float]] = None) -> None:
        """Set vertex data with optimized memory access."""
        if not self.vertex_buffer or vertex_index >= self.vertex_count:
            return

        base_offset = vertex_index * 8  # 8 floats per vertex

        # Position (3 floats)
        self.vertex_buffer[base_offset] = position[0]
        self.vertex_buffer[base_offset + 1] = position[1]
        self.vertex_buffer[base_offset + 2] = position[2]

        # Normal (3 floats)
        if normal:
            self.vertex_buffer[base_offset + 3] = normal[0]
            self.vertex_buffer[base_offset + 4] = normal[1]
            self.vertex_buffer[base_offset + 5] = normal[2]

        # UV (2 floats)
        if uv:
            self.vertex_buffer[base_offset + 6] = uv[0]
            self.vertex_buffer[base_offset + 7] = uv[1]

    def set_face_data(self, face_index: int, vertex_indices: List[int]) -> None:
        """Set face data."""
        if not self.face_buffer or face_index >= self.face_count or len(vertex_indices) != 3:
            return

        base_offset = face_index * 3  # 3 indices per face
        self.face_buffer[base_offset] = vertex_indices[0]
        self.face_buffer[base_offset + 1] = vertex_indices[1]
        self.face_buffer[base_offset + 2] = vertex_indices[2]

    def get_vertex_data(self, vertex_index: int) -> Optional[Dict[str, List[float]]]:
        """Get vertex data."""
        if not self.vertex_buffer or vertex_index >= self.vertex_count:
            return None

        base_offset = vertex_index * 8

        return {
            "position": [
                self.vertex_buffer[base_offset],
                self.vertex_buffer[base_offset + 1],
                self.vertex_buffer[base_offset + 2]
            ],
            "normal": [
                self.vertex_buffer[base_offset + 3],
                self.vertex_buffer[base_offset + 4],
                self.vertex_buffer[base_offset + 5]
            ],
            "uv": [
                self.vertex_buffer[base_offset + 6],
                self.vertex_buffer[base_offset + 7]
            ]
        }

    def get_memory_usage(self) -> Dict[str, int]:
        """Get memory usage statistics."""
        usage = {"total_bytes": 0, "vertex_bytes": 0, "face_bytes": 0}

        if self.vertex_buffer:
            usage["vertex_bytes"] = self.vertex_buffer.itemsize * len(self.vertex_buffer)
            usage["total_bytes"] += usage["vertex_bytes"]

        if self.face_buffer:
            usage["face_bytes"] = self.face_buffer.itemsize * len(self.face_buffer)
            usage["total_bytes"] += usage["face_bytes"]

        return usage


class CADMemoryManager:
    """Comprehensive CAD memory manager with C++ patterns."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.memory_pools: Dict[str, CppStyleMemoryPool] = {}
        self.object_pools: Dict[str, ObjectPool] = {}
        self.stl_pools = STLProcessingPool()
        self.memory_arenas: Dict[str, MemoryArena] = {}
        self.ref_manager = ReferenceCountingManager()

        # Initialize default pools
        self._initialize_default_pools()

    def _initialize_default_pools(self) -> None:
        """Initialize default memory pools."""
        # Small objects pool (for vertices, faces)
        self.memory_pools["small"] = CppStyleMemoryPool(
            initial_size=64 * 1024,  # 64KB
            alignment=MemoryAlignment.DWORD,
            strategy=PoolStrategy.BUDDY_SYSTEM
        )

        # Medium objects pool (for mesh data)
        self.memory_pools["medium"] = CppStyleMemoryPool(
            initial_size=1024 * 1024,  # 1MB
            alignment=MemoryAlignment.CACHE_LINE,
            strategy=PoolStrategy.BEST_FIT
        )

        # Large objects pool (for big meshes)
        self.memory_pools["large"] = CppStyleMemoryPool(
            initial_size=16 * 1024 * 1024,  # 16MB
            alignment=MemoryAlignment.PAGE,
            strategy=PoolStrategy.FIRST_FIT
        )

        # Initialize memory arenas
        self.memory_arenas["vertex_data"] = MemoryArena(size=1024 * 1024)
        self.memory_arenas["face_data"] = MemoryArena(size=512 * 1024)

    def allocate_mesh_buffer(self, vertex_count: int, face_count: int) -> OptimizedMeshBuffer:
        """Allocate optimized mesh buffer."""
        buffer = OptimizedMeshBuffer(vertex_count, face_count)

        # Allocate in appropriate arena
        if vertex_count > 0:
            vertex_memory = self.memory_arenas["vertex_data"].allocate(vertex_count * 32)  # 8 floats * 4 bytes
            if vertex_memory is not None:
                buffer.vertex_buffer = array('f', [0.0] * (vertex_count * 8))

        if face_count > 0:
            face_memory = self.memory_arenas["face_data"].allocate(face_count * 12)  # 3 uint32 * 4 bytes
            if face_memory is not None:
                buffer.face_buffer = array('I', [0] * (face_count * 3))

        self.logger.debug(f"Allocated mesh buffer: {vertex_count} vertices, {face_count} faces")
        return buffer

    def create_object_pool(self, name: str, factory_func: Callable[[], T],
                          initial_size: int = 10, max_size: int = 100,
                          reset_func: Optional[Callable[[T], None]] = None) -> ObjectPool[T]:
        """Create object pool for specific type."""
        pool = ObjectPool(factory_func, initial_size, max_size, reset_func)
        self.object_pools[name] = pool

        self.logger.info(f"Created object pool '{name}' with initial size {initial_size}")
        return pool

    def get_pool_statistics(self) -> Dict[str, Any]:
        """Get comprehensive pool statistics."""
        stats = {
            "memory_pools": {},
            "object_pools": {},
            "arenas": {},
            "reference_counts": len(self.ref_manager.ref_counts)
        }

        # Memory pool stats
        for name, pool in self.memory_pools.items():
            stats["memory_pools"][name] = pool.get_statistics().__dict__

        # Object pool stats
        for name, pool in self.object_pools.items():
            stats["object_pools"][name] = pool.get_stats()

        # Arena stats
        for name, arena in self.memory_arenas.items():
            stats["arenas"][name] = arena.get_usage_stats()

        # STL processing pools
        stats["stl_pools"] = self.stl_pools.get_all_stats()

        return stats

    def optimize_memory_layout(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize data memory layout (C++ struct optimization)."""
        optimized = {}

        # Optimize vertex data for cache efficiency
        if "vertices" in data:
            vertices = data["vertices"]
            if isinstance(vertices, list) and len(vertices) > 0:
                # Transpose vertex data: [x,y,z] -> [x0,y0,z0, x1,y1,z1, ...]
                # This is more cache-friendly for sequential access
                if isinstance(vertices[0], (list, tuple)) and len(vertices[0]) >= 3:
                    transposed = []
                    for i in range(3):  # x, y, z coordinates
                        for vertex in vertices:
                            transposed.append(vertex[i])

                    optimized["vertices_transposed"] = transposed
                    optimized["vertex_layout"] = "aos"  # Array of Structures

        # Optimize face data
        if "faces" in data:
            faces = data["faces"]
            if isinstance(faces, list) and len(faces) > 0:
                # Convert to flat array for better memory access
                if isinstance(faces[0], (list, tuple)) and len(faces[0]) >= 3:
                    flat_faces = []
                    for face in faces:
                        flat_faces.extend(face[:3])  # Take first 3 indices

                    optimized["faces_flat"] = flat_faces
                    optimized["face_layout"] = "flat"

        return optimized

    def cleanup_unused_memory(self) -> Dict[str, Any]:
        """Cleanup unused memory (C++ destructor equivalent)."""
        cleanup_stats = {
            "pools_cleaned": 0,
            "arenas_reset": 0,
            "objects_garbage_collected": 0,
            "memory_freed_mb": 0.0
        }

        # Cleanup memory pools
        for name, pool in self.memory_pools.items():
            # Implementation would clear unused blocks
            cleanup_stats["pools_cleaned"] += 1

        # Reset arenas periodically
        for name, arena in self.memory_arenas.items():
            if arena.get_usage_stats()["utilization_ratio"] > 0.9:
                arena.reset()
                cleanup_stats["arenas_reset"] += 1

        # Force garbage collection
        gc.collect()
        cleanup_stats["objects_garbage_collected"] = gc.get_stats()

        self.logger.info(f"Memory cleanup completed: {cleanup_stats}")
        return cleanup_stats


# Context managers for C++-style RAII
@contextmanager
def memory_pool_context(pool_name: str = "medium"):
    """Context manager for memory pool usage."""
    manager = CADMemoryManager()
    pool = manager.memory_pools.get(pool_name)

    if pool is None:
        raise ValueError(f"Memory pool '{pool_name}' not available")

    try:
        yield pool
    finally:
        # Cleanup would happen here in C++ destructor
        pass


@contextmanager
def mesh_buffer_context(vertex_count: int = 0, face_count: int = 0):
    """Context manager for mesh buffer allocation."""
    manager = CADMemoryManager()
    buffer = manager.allocate_mesh_buffer(vertex_count, face_count)

    try:
        yield buffer
    finally:
        # Buffer cleanup would happen here
        pass


# Factory functions for C++-style instantiation
def create_memory_pool(initial_size: int = 1024 * 1024,
                      alignment: MemoryAlignment = MemoryAlignment.CACHE_LINE,
                      strategy: PoolStrategy = PoolStrategy.BUDDY_SYSTEM) -> CppStyleMemoryPool:
    """Create C++-style memory pool."""
    return CppStyleMemoryPool(initial_size, alignment, strategy)


def create_object_pool(factory_func: Callable[[], T],
                      initial_size: int = 10,
                      max_size: int = 100,
                      reset_func: Optional[Callable[[T], None]] = None) -> ObjectPool[T]:
    """Create object pool."""
    return ObjectPool(factory_func, initial_size, max_size, reset_func)


def create_stl_processing_pool() -> STLProcessingPool:
    """Create STL processing pool."""
    return STLProcessingPool()


def create_memory_arena(size: int = 1024 * 1024) -> MemoryArena:
    """Create memory arena."""
    return MemoryArena(size)


def create_cad_memory_manager() -> CADMemoryManager:
    """Create comprehensive CAD memory manager."""
    return CADMemoryManager()

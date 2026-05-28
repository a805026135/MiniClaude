"""Code Optimization Skill - optimizes code for performance and resource efficiency."""

from __future__ import annotations

from miniclaude.skills.base import BaseSkill, SkillContext, SkillMeta, SkillResult


class CodeOptimizeSkill(BaseSkill):
    """Optimizes code for better performance, lower resource usage, and efficiency."""

    @property
    def meta(self) -> SkillMeta:
        return SkillMeta(
            name="optimize",
            description="Optimize code for performance, memory usage, and resource efficiency. "
                        "Applies algorithmic improvements, caching, and concurrency patterns.",
            tags=[
                "optimize", "performance", "speed", "fast", "efficient",
                "memory", "cache", "并发", "并行", "优化", "加速", "性能",
                "资源", "效率", "瓶颈", "profiling", "benchmark"
            ],
            examples=[
                "optimize this code for speed",
                "make this function faster",
                "improve performance of this module",
                "优化这段代码的性能",
                "reduce memory usage",
                "this code is too slow, help optimize it",
                "optimize the database queries",
                "add caching to improve performance",
                "parallelize this code",
                "fix the performance bottleneck",
                "加速这段代码",
                "减少内存占用",
            ],
            applicable_when="User wants to improve code performance, reduce latency, or optimize resource usage",
            tools_used=["read_file", "write_file", "edit_file", "grep_search", "glob_files", "run_command"],
        )

    async def execute(self, context: SkillContext) -> SkillResult:
        return SkillResult(
            skill_name=self.name,
            success=True,
            instructions="""
## Code Optimization Mode

You are now in code optimization mode. Follow this systematic approach to improve performance:

### 1. Profile & Analyze First
Before optimizing, understand where the bottleneck is:
- Read the code thoroughly to understand the logic
- Identify hot paths (frequently executed code)
- Look for algorithmic inefficiencies (O(n²) where O(n) is possible)
- Check for unnecessary operations (redundant calculations, repeated work)

### 2. Optimization Strategies

#### Algorithm & Data Structure
- Use appropriate data structures (dict/set for O(1) lookup, deque for queue operations)
- Replace nested loops with more efficient algorithms when possible
- Use generators/iterators for large datasets to reduce memory
- Apply divide-and-conquer or dynamic programming when suitable

#### Caching & Memoization
- Add caching for expensive computations (functools.lru_cache, custom caches)
- Cache database queries and API responses appropriately
- Use memoization for recursive functions
- Consider TTL (time-to-live) for cache invalidation

#### I/O Optimization
- Batch database operations instead of N+1 queries
- Use connection pooling for database/network connections
- Implement async I/O for concurrent operations (asyncio, aiohttp)
- Use buffered I/O for file operations
- Compress data for network transfer

#### Memory Optimization
- Use __slots__ for classes with many instances
- Implement generators instead of lists for large sequences
- Release resources explicitly (context managers, del)
- Avoid unnecessary object copies
- Use memory-efficient data structures (array.array for numeric data)

#### Concurrency & Parallelism
- Use asyncio for I/O-bound tasks
- Use multiprocessing for CPU-bound tasks
- Implement thread pools for concurrent operations
- Use concurrent.futures for parallel execution

### 3. Language-Specific Tips

**Python:**
- Use list/dict comprehensions instead of loops
- Prefer built-in functions (map, filter, sum) over manual loops
- Use f-strings instead of format() or % concatenation
- Leverage NumPy/Pandas for numerical computations
- Use PyPy for CPU-intensive pure Python code

**Database:**
- Add proper indexes for frequently queried columns
- Use EXPLAIN to analyze query plans
- Implement pagination for large result sets
- Use bulk insert/update operations

### 4. Output Format

Present optimizations as:

```
## Performance Analysis

### Current Issues
- 🔴 **Critical**: [Issue description with impact]
- 🟡 **Warning**: [Issue description]

### Optimizations Applied

#### 1. [Optimization Name]
**Before:**
```[language]
// Original code
```

**After:**
```[language]
// Optimized code
```

**Impact:** [Expected improvement - e.g., 50% faster, 60% less memory]

### Benchmark Results
If possible, run benchmarks to show before/after performance.

### Recommendations
- Additional optimizations to consider
- Trade-offs (speed vs memory, complexity vs performance)
```

### 5. Safety Rules
- Preserve correctness - optimization must not change behavior
- Measure before and after to verify improvement
- Document any trade-offs (e.g., more memory for speed)
- Keep code readable - don't sacrifice clarity for minor gains
- Consider the 80/20 rule: optimize the critical 20% of code

### 6. Benchmarking
When possible, create simple benchmarks to demonstrate improvement:
```python
import time

start = time.perf_counter()
# Run original code
original_time = time.perf_counter() - start

start = time.perf_counter()
# Run optimized code
optimized_time = time.perf_counter() - start

print(f"Speedup: {original_time/optimized_time:.2f}x")
```
""",
            suggested_tools=["read_file", "write_file", "edit_file", "grep_search", "glob_files", "run_command"],
        )
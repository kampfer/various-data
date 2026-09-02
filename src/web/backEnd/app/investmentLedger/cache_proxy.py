import time
from typing import Any, Dict, Optional, Callable

class CacheManager:
    """缓存管理器：存储所有缓存数据，提供存取和清理接口"""
    def __init__(self):
        self._cache: Dict[str, tuple] = {}   # key -> (value, timestamp)

    def get(self, key: str, ttl: int) -> Optional[Any]:
        """获取缓存，若过期则返回 None"""
        entry = self._cache.get(key)
        if entry:
            value, timestamp = entry
            if time.time() - timestamp < ttl:
                return value
            else:
                del self._cache[key]   # 自动清理过期条目
        return None

    def set(self, key: str, value: Any):
        self._cache[key] = (value, time.time())

    def clear(self, key: Optional[str] = None):
        """清空全部或指定 key 的缓存"""
        if key is None:
            self._cache.clear()
        else:
            self._cache.pop(key, None)

    def clear_by_prefix(self, prefix: str):
        """清除以 prefix 开头的所有缓存键（用于清空某个方法的所有参数缓存）"""
        keys = [k for k in self._cache if k.startswith(prefix)]
        for k in keys:
            del self._cache[k]


class CacheProxy:
    """
    缓存代理：为对象的方法调用添加缓存，缓存数据由外部 CacheManager 管理。
    配置：传入 {method_name: ttl} 字典。
    """
    def __init__(self, target: Any, cache_manager: CacheManager, cache_config: Dict[str, int]):
        self._target = target
        self._cache_manager = cache_manager
        self._cache_config = cache_config

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._target, name)
        if not callable(attr) or name not in self._cache_config:
            return attr   # 不缓存的方法直接返回

        ttl = self._cache_config[name]

        def cached_method(*args, **kwargs):
            force_refresh = kwargs.pop('force_refresh', False)
            # 生成缓存键（包含方法名和参数）
            key = self._make_key(name, args, kwargs)

            if not force_refresh:
                cached = self._cache_manager.get(key, ttl)
                if cached is not None:
                    return cached

            # 执行原方法
            result = attr(*args, **kwargs)
            self._cache_manager.set(key, result)
            return result

        return cached_method

    def _make_key(self, method_name: str, args: tuple, kwargs: dict) -> str:
        parts = [method_name]
        parts.extend(str(arg) for arg in args)
        parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return ":".join(parts)

    def clear_cache(self, method_name: Optional[str] = None):
        """清空全部或指定方法的缓存"""
        if method_name is None:
            self._cache_manager.clear()
        else:
            self._cache_manager.clear_by_prefix(method_name + ":")
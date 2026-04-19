# -*- coding: utf-8 -*-
"""IP Arsenal - 缓存模块
支持 Redis（通过 REDIS_URL 环境变量切换）和内存缓存（默认）"""
import os
import json
import time
from functools import wraps

# Redis 连接
_redis = None
_USE_REDIS = False

REDIS_URL = os.environ.get("REDIS_URL", "")

if REDIS_URL:
    try:
        import redis
        _redis = redis.from_url(REDIS_URL, decode_responses=True)
        _redis.ping()
        _USE_REDIS = True
        print("[Cache] Redis 已连接")
    except Exception as e:
        print(f"[Cache] Redis 连接失败，使用内存缓存: {e}")
        _USE_REDIS = False

# 内存缓存
_memory_cache = {}
_CACHE_TTL = 300  # 默认5分钟

# ─── 缓存操作 ────────────────────────────────────────────────────────

def get(key: str, default=None):
    """获取缓存值"""
    if _USE_REDIS:
        try:
            val = _redis.get(key)
            return json.loads(val) if val else default
        except:
            return default
    else:
        item = _memory_cache.get(key)
        if item is None:
            return default
        # 检查过期
        if item["expire_at"] < time.time():
            del _memory_cache[key]
            return default
        return item["value"]


def set(key: str, value, ttl: int = None):
    """设置缓存值"""
    ttl = ttl or _CACHE_TTL
    if _USE_REDIS:
        try:
            _redis.setex(key, ttl, json.dumps(value, ensure_ascii=False))
        except:
            pass
    else:
        _memory_cache[key] = {
            "value": value,
            "expire_at": time.time() + ttl
        }


def delete(key: str):
    """删除缓存"""
    if _USE_REDIS:
        try:
            _redis.delete(key)
        except:
            pass
    else:
        _memory_cache.pop(key, None)


def clear_prefix(prefix: str):
    """清除指定前缀的所有缓存"""
    if _USE_REDIS:
        try:
            keys = _redis.keys(prefix + "*")
            if keys:
                _redis.delete(*keys)
        except:
            pass
    else:
        to_del = [k for k in _memory_cache if k.startswith(prefix)]
        for k in to_del:
            del _memory_cache[k]


def cached(key_prefix: str, ttl: int = 300):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存 key
            cache_key = key_prefix + ":" + str(args[0]) if args else key_prefix
            # 尝试获取缓存
            cached_val = get(cache_key)
            if cached_val is not None:
                return cached_val
            # 执行函数
            result = func(*args, **kwargs)
            # 设置缓存
            set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator


# ─── 常用缓存 key 前缀 ───────────────────────────────────────────────
CACHE_KEYS = {
    "stats": "iparsenal:stats",
    "materials_list": "iparsenal:materials:list:",
    "sources_list": "iparsenal:sources:list",
    "queue_status": "iparsenal:queue:status",
}

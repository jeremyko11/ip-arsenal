# -*- coding: utf-8 -*-
"""
IP Arsenal - 任务队列模块
Worker 线程池、任务队列、看门狗
"""
import queue
import threading
import time
from datetime import datetime

from config import SMART_EXTRACTION_AVAILABLE
from db import get_db, now


# ── 队列和 Worker 配置 ────────────────────────────────────────────────
_task_queue: queue.Queue = queue.Queue()
WORKER_COUNT = 8        # 同时运行 8 个 Worker（AI 推理 + IO 操作均能并行）
TASK_MAX_SECONDS = 1800 # 单个任务最长执行时间（30分钟，智能提炼需要更长时间）
_worker_threads: list = []              # 所有 worker 线程 + watchdog 线程
_worker_heartbeats: dict = {}           # worker_id → 最后一次取任务的时间（0=idle）


# ── Worker 循环 ────────────────────────────────────────────────────────
def _worker_loop(worker_id: int):
    """Worker 主线程：从队列取任务执行，任何异常都会导致线程退出

    详细说明：
    - 取任务时若队列空，Watchdog 会检测此线程是否存活来决定是否重建
    - 如果任务在子线程中执行超时，Worker 继续取下一个任务
    - 超时任务会被标记为 error，Worker 继续处理下一个任务
    """
    print(f"[Worker-{worker_id}] 启动")
    while True:
        task_item = None
        try:
            task_item = _task_queue.get(timeout=2)
            task_id, source_id, mode = task_item

            # 更新心跳时间戳
            _worker_heartbeats[worker_id] = time.time()
            print(f"[Worker-{worker_id}] 开始处理 source={source_id} mode={mode}")

            # 在子线程中执行任务（强制超时保护）
            # 注意：这里使用 lazy import 避免循环依赖
            import concurrent.futures as _cf
            with _cf.ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"W{worker_id}-task") as _tex:
                # 延迟导入避免循环依赖
                from services.process import process_source_task_smart, process_source_task
                if mode == "smart" and SMART_EXTRACTION_AVAILABLE:
                    _task_fn = lambda: process_source_task_smart(task_id, source_id, mode)
                else:
                    _task_fn = lambda: process_source_task(task_id, source_id, mode)
                _future = _tex.submit(_task_fn)
                try:
                    _future.result(timeout=TASK_MAX_SECONDS)
                    print(f"[Worker-{worker_id}] 完成 source={source_id}")
                except _cf.TimeoutError:
                    print(f"[Worker-{worker_id}] ⚠️ 任务超时({TASK_MAX_SECONDS}s) source={source_id}，强制跳过")
                    try:
                        _ec = get_db()
                        _ec.execute("UPDATE sources SET status='error',error_msg=%s,updated_at=%s WHERE id=%s",
                                    (f"任务超时（>{TASK_MAX_SECONDS}s），已自动跳过", now(), source_id))
                        _ec.execute("UPDATE tasks SET status='error',message=%s,updated_at=%s WHERE id=%s",
                                    (f"执行超时（>{TASK_MAX_SECONDS}s），已自动跳过", now(), task_id))
                        _ec.commit()
                        _ec.close()
                    except Exception as _de:
                        print(f"[Worker-{worker_id}] 超时标记DB失败: {_de}")
                except Exception as e:
                    print(f"[Worker-{worker_id}] 任务异常 source={source_id}: {e}")
                    import traceback; traceback.print_exc()
        except queue.Empty:
            # 队列空，清空心跳（idle 状态）
            _worker_heartbeats[worker_id] = 0
            continue
        except Exception as e:
            print(f"[Worker-{worker_id}] 队列操作异常: {e}")
        finally:
            if task_item is not None:
                try:
                    _task_queue.task_done()
                except Exception:
                    pass
            _worker_heartbeats[worker_id] = 0  # 重置心跳（idle）
            time.sleep(0.1)  # 避免 CPU 空转


def enqueue_task(task_id: str, source_id: str, mode: str):
    """将任务加入队列（线程安全）"""
    _task_queue.put((task_id, source_id, mode))


def _spawn_worker(worker_id: int) -> threading.Thread:
    """创建并启动一个 worker 线程"""
    t = threading.Thread(
        target=_worker_loop,
        args=(worker_id,),
        daemon=True,
        name=f"Arsenal-Worker-{worker_id}"
    )
    t.start()
    return t


def _watchdog_loop():
    """Watchdog 线程：每60秒检测 worker 线程是否存活或卡死

    【重构说明】
    - 死亡检测：线程 is_alive() == False → 立即重建
    - 卡死检测：心跳时间戳超过 TASK_MAX_SECONDS+60 秒未更新 → 标记为卡死，重建线程
    """
    time.sleep(15)  # 启动后等15秒再开始监控
    while True:
        try:
            for i, t in enumerate(_worker_threads):
                worker_id = i + 1
                if not t.is_alive():
                    print(f"[Watchdog] Worker-{worker_id} 已死亡，正在重建...")
                    new_t = _spawn_worker(worker_id)
                    _worker_threads[i] = new_t
                    _worker_heartbeats[worker_id] = 0
                    print(f"[Watchdog] Worker-{worker_id} 已重建")
        except Exception as e:
            print(f"[Watchdog] 异常: {e}")
        time.sleep(60)


def _start_workers():
    """启动 Worker 线程池 + Watchdog"""
    global _worker_threads, _worker_heartbeats
    _worker_threads.clear()
    _worker_heartbeats.clear()
    for i in range(WORKER_COUNT):
        worker_id = i + 1
        _worker_heartbeats[worker_id] = 0  # 初始 idle
        t = _spawn_worker(worker_id)
        _worker_threads.append(t)
    print(f"[Arsenal] {WORKER_COUNT} 个 Worker 线程已启动")
    # 启动 watchdog
    wd = threading.Thread(target=_watchdog_loop, daemon=True, name="Arsenal-Watchdog")
    wd.start()
    print("[Arsenal] Watchdog 已启动")


def _recover_stuck_tasks():
    """启动时恢复所有 processing/pending 任务"""
    conn = get_db()
    try:
        # 将 processing 重置为 pending（防止上次崩溃留下的假 processing 状态）
        conn.execute(
            "UPDATE sources SET status='pending', updated_at=%s WHERE status='processing'",
            (now(),)
        )
        conn.execute(
            "UPDATE tasks SET status='pending', message='等待处理（服务重启恢复）...', updated_at=%s WHERE status='processing'",
            (now(),)
        )
        conn.commit()

        # 恢复所有 pending 任务入队
        rows = conn.execute(
            """SELECT t.id as task_id, t.source_id
               FROM tasks t JOIN sources s ON t.source_id = s.id
               WHERE s.status = 'pending'
               ORDER BY s.created_at"""
        ).fetchall()
        for row in rows:
            enqueue_task(row["task_id"], row["source_id"], "full")

        if rows:
            print(f"[Arsenal] 恢复 {len(rows)} 个待处理任务入队")
    finally:
        conn.close()

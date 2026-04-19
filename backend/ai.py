# -*- coding: utf-8 -*-
"""
IP Arsenal - AI 调用模块
AI 调用链、超时处理、降级策略
"""
import re
import concurrent.futures
from typing import Optional

from config import (
    client, fallback_client, fallback2_client, get_minimax2_client,
    MODEL_ID, MINIMAX_MODEL_ID, MINIMAX_MODEL_ID_2, FALLBACK2_MODEL_ID,
    FALLBACK_MODEL_ID, _AI_PREFERRED,
)


def strip_think_tags(text: str) -> str:
    """去掉 <think>...</think> 推理过程标签"""
    import re as _re
    # 去掉 <think>...</think> 块（可能跨多行）
    # 使用两个占位符来安全处理多行模式
    _START = "<|THINK_START|>"
    _END = "<|THINK_END|>"
    text = text.replace("<think>", _START).replace("</think>", _END)
    text = _re.sub(r"<\|THINK_START\|>[\s\S]*?<\|THINK_END\|>", "", text, flags=_re.IGNORECASE)
    text = text.replace(_START, "").replace(_END, "")
    return text.strip()


def _is_quota_error(err_str: str) -> bool:
    """判断是否为余额不足/配额耗尽错误，是则立即跳过，不必等待超时"""
    LOW = err_str.lower()
    return any(k in LOW for k in (
        "insufficient_quota", "insufficient quota", "402",
        "颍额不足", "额度不足", "quota", "billing", "balance",
        "rate_limit_exceeded", "you exceeded your current quota",
    ))


def _call_ai_with_timeout(
    ai_client,
    model_id: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    temperature: float,
    timeout_secs: int = 180,
) -> str:
    """在独立线程中调用AI，使用concurrent.futures实现强制超时"""
    def _do_call():
        resp = ai_client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return resp.choices[0].message.content or ""

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_do_call)
        try:
            return future.result(timeout=timeout_secs)
        except concurrent.futures.TimeoutError:
            raise TimeoutError(f"AI接口超过{timeout_secs}秒未响应，强制中断")


def _build_model_chain() -> list:
    """根据 _AI_PREFERRED 构建 AI 调用链（从首选模型开始，失败依次降级）"""
    _ALL = {
        "xunfei":   ("详飞",   lambda: client,              MODEL_ID,          300, False),
        "minimax":  ("MiniMax", lambda: fallback_client,    MINIMAX_MODEL_ID,   60, True),
        "minimax2": ("MiniMax2",lambda: get_minimax2_client(), MINIMAX_MODEL_ID_2, 480, True),
        "deepseek": ("DeepSeek",lambda: fallback2_client,   FALLBACK2_MODEL_ID,300, True),
    }
    _DEFAULT_ORDER = ["xunfei", "minimax", "minimax2", "deepseek"]
    preferred = _AI_PREFERRED if _AI_PREFERRED in _ALL else "xunfei"
    order = [preferred] + [k for k in _DEFAULT_ORDER if k != preferred]
    chain = []
    for key in order:
        label, getter, model_id, timeout, strip = _ALL[key]
        if key == "minimax2" and not get_minimax2_client():
            continue
        chain.append((label, getter, model_id, timeout, strip))
    return chain


def ai_extract(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 12000,
    temperature: float = 0.7,
) -> tuple:
    """调用 AI 提炼，根据 _AI_PREFERRED 决定起点，自动降级"""
    chain = _build_model_chain()
    errors = []

    for label, getter, model_id, timeout, should_strip in chain:
        ai_client = getter()
        if ai_client is None:
            continue
        try:
            content = _call_ai_with_timeout(
                ai_client, model_id, system_prompt, user_prompt,
                max_tokens, temperature, timeout_secs=timeout
            )
            if should_strip:
                content = strip_think_tags(content)
            print(f"[AI] {label} 成功，model={model_id}，耗时约 {timeout}s")
            return content, model_id
        except Exception as _ex:
            err = str(_ex)[:300]
            errors.append(f"{label}:{err[:120]}")
            if _is_quota_error(err):
                print(f"[AI] {label} 余额/额度不足，切换下一个...")
            else:
                print(f"[AI] {label} 失败: {err[:120]}，切换下一个...")

    raise RuntimeError("所有 AI 模型均失败 | " + " | ".join(errors))

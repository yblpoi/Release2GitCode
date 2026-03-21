"""ServerChan3 notifications."""

from __future__ import annotations

import re

import httpx

from release2gitcode.core.errors import NetworkError
from release2gitcode.core.models import SyncResult


SENDKEY_UID_RE = re.compile(r"^sctp(\d+)t")


def extract_serverchan_uid(sendkey: str) -> str:
    match = SENDKEY_UID_RE.match(sendkey)
    if not match:
        raise ValueError("Unable to extract uid from ServerChan3 SendKey")
    return match.group(1)


def _format_bytes(bytes_value: int) -> str:
    """格式化字节数为易读的单位"""
    if bytes_value == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(bytes_value)
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    return f"{size:.2f} {units[unit_index]}"


def _calculate_speed(total_bytes: int, duration_seconds: float) -> str:
    """计算传输速度"""
    if duration_seconds <= 0 or total_bytes == 0:
        return "0.00 MB/s"
    speed_mbps = (total_bytes / (1024 * 1024)) / duration_seconds
    return f"{speed_mbps:.2f} MB/s"


def build_serverchan_payload(result: SyncResult) -> dict[str, str]:
    """构建优化的Server酱推送内容"""
    status_emoji = "✅" if result.is_success else "❌"
    status_text = "同步成功" if result.is_success else "同步失败"
    
    if result.is_success:
        title = f"{status_emoji} {status_text} | 处理{result.processed_assets}个文件 | 耗时{result.duration_seconds:.1f}秒"
    else:
        title = f"{status_emoji} {status_text} | 失败{len(result.failed_assets)}个文件 | 耗时{result.duration_seconds:.1f}秒"
    
    lines = []
    
    lines.append(f"## {status_emoji} {status_text}")
    lines.append("")
    
    lines.append("### 📋 基本信息")
    lines.append(f"- **触发时间**：{result.triggered_at}")
    lines.append(f"- **任务ID**：`{result.task_id}`")
    lines.append("")
    
    lines.append("### 📊 同步统计")
    lines.append(f"- **总文件数**：{result.total_assets}")
    lines.append(f"- **成功处理**：{result.processed_assets}")
    lines.append(f"- **跳过文件**：{result.skipped_assets}")
    lines.append(f"- **失败文件**：{len(result.failed_assets)}")
    lines.append("")
    
    lines.append("### ⚡ 性能信息")
    if result.total_bytes > 0:
        total_size = _format_bytes(result.total_bytes)
        avg = _format_bytes(result.total_bytes // result.processed_assets) if result.processed_assets > 0 else "0 B"
        speed = _calculate_speed(result.total_bytes, result.duration_seconds)
        lines.append(f"- **总大小**：{total_size}")
        lines.append(f"- **平均大小**：{avg}")
        lines.append(f"- **传输速度**：{speed}")
    else:
        lines.append("- 无文件传输数据")
    lines.append("")
    
    lines.append("---")
    lines.append("")
    
    lines.append("### 🔗 链接信息")
    lines.append(f"- **GitHub发行版**：[{result.github_release_url}]({result.github_release_url})")
    lines.append(f"- **GitCode仓库**：[{result.gitcode_repo_url}]({result.gitcode_repo_url})")
    lines.append("")
    
    if result.failed_assets:
        lines.append("---")
        lines.append("")
        lines.append("### ⚠️ 失败详情")
        lines.append("以下文件同步失败：")
        lines.append("")
        for failed_asset in result.failed_assets[:10]:
            lines.append(f"- ❌ {failed_asset}")
        if len(result.failed_assets) > 10:
            lines.append(f"- ... 还有 {len(result.failed_assets) - 10} 个失败文件")
        lines.append("")
    
    desp = "\n".join(lines)
    
    return {
        "title": title,
        "desp": desp,
        "short": title,
        "tags": "release2gitcode|gitcode|sync",
    }


async def send_serverchan_notification(client: httpx.AsyncClient, sendkey: str, result: SyncResult) -> None:
    uid = extract_serverchan_uid(sendkey)
    url = f"https://{uid}.push.ft07.com/send/{sendkey}.send"
    try:
        response = await client.post(url, json=build_serverchan_payload(result))
    except httpx.RequestError as exc:
        raise NetworkError(f"ServerChan3 notification failed: {exc}") from exc
    if response.status_code >= 400:
        raise NetworkError(f"ServerChan3 notification failed: HTTP {response.status_code} {response.text[:200]}")

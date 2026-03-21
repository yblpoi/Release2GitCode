"""测试notifications模块的单元测试"""

import pytest

from release2gitcode.core.models import SyncResult
from release2gitcode.core.notifications import build_serverchan_payload, _format_bytes, _calculate_speed


class TestFormatBytes:
    """测试字节格式化函数"""

    def test_zero_bytes(self):
        """测试0字节的格式化"""
        assert _format_bytes(0) == "0 B"

    def test_bytes(self):
        """测试字节的格式化"""
        assert _format_bytes(500) == "500.00 B"
        assert _format_bytes(1023) == "1023.00 B"

    def test_kilobytes(self):
        """测试千字节的格式化"""
        assert _format_bytes(1024) == "1.00 KB"
        assert _format_bytes(1536) == "1.50 KB"
        assert _format_bytes(1048575) == "1024.00 KB"

    def test_megabytes(self):
        """测试兆字节的格式化"""
        assert _format_bytes(1048576) == "1.00 MB"
        assert _format_bytes(1572864) == "1.50 MB"
        assert _format_bytes(1073741823) == "1024.00 MB"

    def test_gigabytes(self):
        """测试吉字节的格式化"""
        assert _format_bytes(1073741824) == "1.00 GB"
        assert _format_bytes(1610612736) == "1.50 GB"


class TestCalculateSpeed:
    """测试速度计算函数"""

    def test_zero_bytes(self):
        """测试0字节的速度计算"""
        assert _calculate_speed(0, 10.0) == "0.00 MB/s"

    def test_zero_duration(self):
        """测试0时长的速度计算"""
        assert _calculate_speed(1048576, 0) == "0.00 MB/s"

    def test_normal_speed(self):
        """测试正常速度计算"""
        assert _calculate_speed(1048576, 1.0) == "1.00 MB/s"
        assert _calculate_speed(10485760, 10.0) == "1.00 MB/s"
        assert _calculate_speed(5242880, 2.0) == "2.50 MB/s"

    def test_fast_speed(self):
        """测试高速计算"""
        assert _calculate_speed(104857600, 1.0) == "100.00 MB/s"


class TestBuildServerchanPayload:
    """测试Server酱推送内容构建"""

    def test_success_sync_title(self):
        """测试成功同步的标题"""
        result = SyncResult(
            task_id="test-task-1",
            triggered_at="2024-01-01 12:00:00 UTC",
            github_release_url="https://github.com/owner/repo/releases/tag/v1.0.0",
            gitcode_repo_url="https://gitcode.com/owner/repo",
            processed_assets=5,
            skipped_assets=2,
            failed_assets=[],
            total_assets=7,
            duration_seconds=10.5,
            total_bytes=5242880,
        )
        payload = build_serverchan_payload(result)
        assert "✅" in payload["title"]
        assert "同步成功" in payload["title"]
        assert "处理5个文件" in payload["title"]
        assert "耗时10.5秒" in payload["title"]

    def test_failed_sync_title(self):
        """测试失败同步的标题"""
        result = SyncResult(
            task_id="test-task-2",
            triggered_at="2024-01-01 12:00:00 UTC",
            github_release_url="https://github.com/owner/repo/releases/tag/v1.0.0",
            gitcode_repo_url="https://gitcode.com/owner/repo",
            processed_assets=3,
            skipped_assets=0,
            failed_assets=["file1.zip", "file2.tar.gz"],
            total_assets=5,
            duration_seconds=15.2,
            total_bytes=3145728,
        )
        payload = build_serverchan_payload(result)
        assert "❌" in payload["title"]
        assert "同步失败" in payload["title"]
        assert "失败2个文件" in payload["title"]
        assert "耗时15.2秒" in payload["title"]

    def test_success_sync_content(self):
        """测试成功同步的内容"""
        result = SyncResult(
            task_id="test-task-3",
            triggered_at="2024-01-01 12:00:00 UTC",
            github_release_url="https://github.com/owner/repo/releases/tag/v1.0.0",
            gitcode_repo_url="https://gitcode.com/owner/repo",
            processed_assets=3,
            skipped_assets=1,
            failed_assets=[],
            total_assets=4,
            duration_seconds=8.0,
            total_bytes=3145728,
        )
        payload = build_serverchan_payload(result)
        desp = payload["desp"]
        
        assert "## ✅ 同步成功" in desp
        assert "### 📋 基本信息" in desp
        assert "触发时间" in desp
        assert "test-task-3" in desp
        assert "### 📊 同步统计" in desp
        assert "总文件数**：4" in desp
        assert "成功处理**：3" in desp
        assert "跳过文件**：1" in desp
        assert "失败文件**：0" in desp
        assert "### ⚡ 性能信息" in desp
        assert "### 🔗 链接信息" in desp
        assert "https://github.com/owner/repo/releases/tag/v1.0.0" in desp
        assert "https://gitcode.com/owner/repo" in desp

    def test_failed_sync_with_failed_assets(self):
        """测试有失败文件的同步内容"""
        result = SyncResult(
            task_id="test-task-4",
            triggered_at="2024-01-01 12:00:00 UTC",
            github_release_url="https://github.com/owner/repo/releases/tag/v1.0.0",
            gitcode_repo_url="https://gitcode.com/owner/repo",
            processed_assets=2,
            skipped_assets=0,
            failed_assets=["failed1.zip", "failed2.tar.gz", "failed3.exe"],
            total_assets=5,
            duration_seconds=12.0,
            total_bytes=2097152,
        )
        payload = build_serverchan_payload(result)
        desp = payload["desp"]
        
        assert "## ❌ 同步失败" in desp
        assert "### ⚠️ 失败详情" in desp
        assert "failed1.zip" in desp
        assert "failed2.tar.gz" in desp
        assert "failed3.exe" in desp

    def test_many_failed_assets_truncation(self):
        """测试大量失败文件的截断"""
        failed_assets = [f"file{i}.zip" for i in range(15)]
        result = SyncResult(
            task_id="test-task-5",
            triggered_at="2024-01-01 12:00:00 UTC",
            github_release_url="https://github.com/owner/repo/releases/tag/v1.0.0",
            gitcode_repo_url="https://gitcode.com/owner/repo",
            processed_assets=0,
            skipped_assets=0,
            failed_assets=failed_assets,
            total_assets=15,
            duration_seconds=20.0,
            total_bytes=0,
        )
        payload = build_serverchan_payload(result)
        desp = payload["desp"]
        
        assert "file0.zip" in desp
        assert "file9.zip" in desp
        assert "还有 5 个失败文件" in desp
        assert "file14.zip" not in desp

    def test_no_bytes_transferred(self):
        """测试无字节传输的情况"""
        result = SyncResult(
            task_id="test-task-6",
            triggered_at="2024-01-01 12:00:00 UTC",
            github_release_url="https://github.com/owner/repo/releases/tag/v1.0.0",
            gitcode_repo_url="https://gitcode.com/owner/repo",
            processed_assets=0,
            skipped_assets=5,
            failed_assets=[],
            total_assets=5,
            duration_seconds=1.0,
            total_bytes=0,
        )
        payload = build_serverchan_payload(result)
        desp = payload["desp"]
        
        assert "无文件传输数据" in desp

    def test_payload_structure(self):
        """测试推送负载的结构"""
        result = SyncResult(
            task_id="test-task-7",
            triggered_at="2024-01-01 12:00:00 UTC",
            github_release_url="https://github.com/owner/repo/releases/tag/v1.0.0",
            gitcode_repo_url="https://gitcode.com/owner/repo",
            processed_assets=1,
            skipped_assets=0,
            failed_assets=[],
            total_assets=1,
            duration_seconds=5.0,
            total_bytes=1048576,
        )
        payload = build_serverchan_payload(result)
        
        assert "title" in payload
        assert "desp" in payload
        assert "short" in payload
        assert "tags" in payload
        assert payload["tags"] == "release2gitcode|gitcode|sync"
        assert payload["short"] == payload["title"]

    def test_file_size_and_speed_calculation(self):
        """测试文件大小和速度计算"""
        result = SyncResult(
            task_id="test-task-8",
            triggered_at="2024-01-01 12:00:00 UTC",
            github_release_url="https://github.com/owner/repo/releases/tag/v1.0.0",
            gitcode_repo_url="https://gitcode.com/owner/repo",
            processed_assets=2,
            skipped_assets=0,
            failed_assets=[],
            total_assets=2,
            duration_seconds=2.0,
            total_bytes=2097152,
        )
        payload = build_serverchan_payload(result)
        desp = payload["desp"]
        
        assert "2.00 MB" in desp
        assert "1.00 MB" in desp
        assert "1.00 MB/s" in desp

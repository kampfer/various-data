"""受控估值采集器注册表；只发现白名单目录中的静态 manifest。"""

from __future__ import annotations

import ast
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import importlib
import importlib.util
import json
from pathlib import Path
import re
import tomllib
from typing import Any, cast

from .protocol import CollectorManifest, ValuationCollector, SUPPORTED_PRODUCT_TYPES


class CollectorRegistrationError(ValueError):
    """采集器 manifest、入口或注册身份不符合受控加载规则。"""


@dataclass(frozen=True, slots=True)
class CollectorMetadata:
    """已登记采集器的只读审计元数据，不包含数据库对象或凭据。"""

    manifest: CollectorManifest
    manifest_path: Path | None
    source_priority: int | None


class CollectorRegistry:
    """只从核心 collectors 目录及显式受信目录加载采集器。

    注册表不接受任意模块名或文件路径。静态发现先验证 manifest 和入口文件的
    真实路径，再导入工厂并比对插件自声明，避免新增数据源时触及账本业务层。
    """

    _IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    _VERSION_PATTERN = re.compile(
        r"^\d+\.\d+\.\d+(?:[-+][A-Za-z0-9][A-Za-z0-9.-]*)?$"
    )
    _MODULE_PATTERN = re.compile(r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*$")
    _FORBIDDEN_IMPORT_PREFIXES = (
        "sqlalchemy",
        "app.database",
        "app.investmentLedger.models",
        "app.investmentLedger.crud",
        "app.investmentLedger.valuation_ingest.repository",
    )

    def __init__(
        self,
        collectors: Iterable[ValuationCollector] = (),
        *,
        trustedDirectories: Iterable[Path | str] = (),
        sourcePriority: Mapping[str, int] | None = None,
    ) -> None:
        """装配显式采集器和受信目录；不会扫描工作区其它位置。"""
        self._collectors: dict[str, ValuationCollector] = {}
        self._metadata: dict[str, CollectorMetadata] = {}
        self._errors: list[str] = []
        self._sourcePriority = dict(sourcePriority or {})
        packageRoot = Path(__file__).resolve().parent.parent
        defaultDirectory = packageRoot / "collectors"
        suppliedDirectories = [Path(directory).resolve() for directory in trustedDirectories]
        self._trustedDirectories = self._uniquePaths([defaultDirectory, *suppliedDirectories])
        for collector in collectors:
            self.register(collector)

    @staticmethod
    def _uniquePaths(paths: Iterable[Path]) -> tuple[Path, ...]:
        """按解析后的绝对路径去重，保持声明顺序。"""
        unique: list[Path] = []
        for path in paths:
            resolved = path.resolve()
            if resolved not in unique:
                unique.append(resolved)
        return tuple(unique)

    @staticmethod
    def _isWithin(path: Path, directory: Path) -> bool:
        """判断路径是否位于受信目录内，防止 ``..`` 与符号链接逃逸。"""
        try:
            path.resolve().relative_to(directory.resolve())
        except ValueError:
            return False
        return True

    @classmethod
    def _validateManifest(cls, manifest: CollectorManifest) -> None:
        """校验身份、版本、来源、能力和入口的静态格式。"""
        if not isinstance(manifest, CollectorManifest):
            raise CollectorRegistrationError("采集器 manifest 类型无效")
        if not cls._IDENTIFIER_PATTERN.fullmatch(manifest.plugin_id):
            raise CollectorRegistrationError("采集器标识格式无效")
        if not cls._VERSION_PATTERN.fullmatch(manifest.version):
            raise CollectorRegistrationError("采集器版本必须是语义版本")
        if not cls._IDENTIFIER_PATTERN.fullmatch(manifest.source_id):
            raise CollectorRegistrationError("采集器来源标识格式无效")
        if not isinstance(manifest.product_types, frozenset) or (
            not manifest.product_types or not manifest.product_types <= SUPPORTED_PRODUCT_TYPES
        ):
            raise CollectorRegistrationError("采集器产品能力集合无效")
        if not isinstance(manifest.enabled, bool):
            raise CollectorRegistrationError("采集器启用标记无效")
        moduleName, separator, factoryName = manifest.entrypoint.partition(":")
        if (
            separator != ":"
            or not cls._MODULE_PATTERN.fullmatch(moduleName)
            or not factoryName.isidentifier()
        ):
            raise CollectorRegistrationError("采集器入口格式无效")

    @classmethod
    def _manifestFromData(cls, data: Mapping[str, Any]) -> CollectorManifest:
        """把 JSON/TOML 静态声明转换为不可变 manifest 值对象。"""
        required = {"plugin_id", "version", "source_id", "product_types", "entrypoint"}
        missing = required - data.keys()
        if missing:
            raise CollectorRegistrationError(f"采集器 manifest 缺少字段：{', '.join(sorted(missing))}")
        productTypes = data["product_types"]
        if not isinstance(productTypes, list) or not all(
            isinstance(item, str) for item in productTypes
        ):
            raise CollectorRegistrationError("采集器产品能力必须是字符串列表")
        enabled = data.get("enabled", True)
        manifest = CollectorManifest(
            plugin_id=cast(str, data["plugin_id"]),
            version=cast(str, data["version"]),
            source_id=cast(str, data["source_id"]),
            product_types=frozenset(productTypes),
            entrypoint=cast(str, data["entrypoint"]),
            enabled=cast(bool, enabled),
        )
        cls._validateManifest(manifest)
        return manifest

    @classmethod
    def _readManifest(cls, manifestPath: Path) -> CollectorManifest:
        """读取受信目录中的 JSON 或 TOML manifest，拒绝其它格式。"""
        try:
            if manifestPath.suffix == ".json":
                data = json.loads(manifestPath.read_text(encoding="utf-8"))
            elif manifestPath.suffix == ".toml":
                data = tomllib.loads(manifestPath.read_text(encoding="utf-8"))
            else:
                raise CollectorRegistrationError("采集器 manifest 格式不受支持")
        except (OSError, json.JSONDecodeError, tomllib.TOMLDecodeError) as error:
            raise CollectorRegistrationError(f"无法读取采集器 manifest：{manifestPath}") from error
        if not isinstance(data, dict):
            raise CollectorRegistrationError("采集器 manifest 必须是对象")
        return cls._manifestFromData(data)

    def _trustedEntrypointPath(self, manifest: CollectorManifest) -> Path:
        """解析入口模块文件并确认其物理位置位于一个受信目录内。"""
        moduleName = manifest.entrypoint.partition(":")[0]
        try:
            spec = importlib.util.find_spec(moduleName)
        except (ImportError, AttributeError, ValueError) as error:
            raise CollectorRegistrationError("采集器入口模块无法解析") from error
        if spec is None or spec.origin is None or spec.origin in {"built-in", "frozen"}:
            raise CollectorRegistrationError("采集器入口模块不存在可验证的文件")
        sourcePath = Path(spec.origin).resolve()
        if not any(self._isWithin(sourcePath, directory) for directory in self._trustedDirectories):
            raise CollectorRegistrationError("采集器入口不在受信目录")
        return sourcePath

    @classmethod
    def _validatePluginSource(cls, sourcePath: Path) -> None:
        """拒绝插件直接导入数据库、模型或 SQLAlchemy 写入能力。"""
        try:
            tree = ast.parse(sourcePath.read_text(encoding="utf-8"), filename=str(sourcePath))
        except (OSError, SyntaxError, UnicodeDecodeError) as error:
            raise CollectorRegistrationError("采集器源码无法安全检查") from error
        for node in ast.walk(tree):
            moduleName = ""
            if isinstance(node, ast.Import):
                for alias in node.names:
                    moduleName = alias.name
                    if moduleName.startswith(cls._FORBIDDEN_IMPORT_PREFIXES):
                        raise CollectorRegistrationError("采集器不得导入数据库连接或模型")
            elif isinstance(node, ast.ImportFrom):
                moduleName = node.module or ""
                if moduleName.startswith(cls._FORBIDDEN_IMPORT_PREFIXES):
                    raise CollectorRegistrationError("采集器不得导入数据库连接或模型")

    def _validatePriority(self, manifest: CollectorManifest) -> int | None:
        """校验核心来源优先级，并拒绝不同启用来源使用相同优先级。"""
        if not self._sourcePriority:
            return None
        priority = self._sourcePriority.get(manifest.source_id)
        if not isinstance(priority, int) or isinstance(priority, bool):
            raise CollectorRegistrationError("采集器来源未配置有效优先级")
        for metadata in self._metadata.values():
            existing = metadata.manifest
            if (
                existing.enabled
                and existing.source_id != manifest.source_id
                and metadata.source_priority == priority
            ):
                raise CollectorRegistrationError("多个启用来源的优先级冲突")
        return priority

    def register(
        self,
        collector: ValuationCollector,
        *,
        declaredManifest: CollectorManifest | None = None,
        manifestPath: Path | None = None,
    ) -> None:
        """登记已验证实例；静态 manifest 必须与插件自声明逐字段一致。"""
        manifest = getattr(collector, "manifest", None)
        self._validateManifest(manifest)
        if declaredManifest is not None and manifest != declaredManifest:
            raise CollectorRegistrationError("采集器自声明与静态 manifest 不一致")
        if not callable(getattr(collector, "collect", None)):
            raise CollectorRegistrationError("采集器未实现 collect 入口")
        if manifest.plugin_id in self._collectors or manifest.plugin_id in self._metadata:
            raise CollectorRegistrationError("采集器标识或版本重复")
        priority = self._validatePriority(manifest)
        self._metadata[manifest.plugin_id] = CollectorMetadata(
            manifest=manifest,
            manifest_path=manifestPath.resolve() if manifestPath else None,
            source_priority=priority,
        )
        if manifest.enabled:
            self._collectors[manifest.plugin_id] = collector

    def discover(self) -> list[CollectorMetadata]:
        """扫描受信目录的 ``manifests``，逐项隔离失败并记录可审计错误。"""
        discovered: list[CollectorMetadata] = []
        for directory in self._trustedDirectories:
            manifestDirectory = directory / "manifests"
            if not manifestDirectory.is_dir():
                continue
            for manifestPath in sorted(
                [*manifestDirectory.glob("*.json"), *manifestDirectory.glob("*.toml")]
            ):
                try:
                    if not self._isWithin(manifestPath, directory):
                        raise CollectorRegistrationError("采集器 manifest 不在受信目录")
                    manifest = self._readManifest(manifestPath)
                    sourcePath = self._trustedEntrypointPath(manifest)
                    self._validatePluginSource(sourcePath)
                    moduleName, _, factoryName = manifest.entrypoint.partition(":")
                    factory = getattr(importlib.import_module(moduleName), factoryName, None)
                    if not callable(factory):
                        raise CollectorRegistrationError("采集器入口工厂不可调用")
                    collector = factory()
                    self.register(
                        collector,
                        declaredManifest=manifest,
                        manifestPath=manifestPath,
                    )
                    discovered.append(self._metadata[manifest.plugin_id])
                except (CollectorRegistrationError, ImportError, AttributeError, TypeError) as error:
                    self._errors.append(f"{manifestPath}: {error}")
        return discovered

    @property
    def metadata(self) -> tuple[CollectorMetadata, ...]:
        """返回所有已登记采集器的审计元数据（包括显式禁用项）。"""
        return tuple(self._metadata.values())

    @property
    def errors(self) -> tuple[str, ...]:
        """返回受控发现期间记录的错误，不暴露插件异常栈。"""
        return tuple(self._errors)

    def get(self, pluginId: str) -> ValuationCollector:
        """按受信采集器标识获取已启用实例。"""
        try:
            return self._collectors[pluginId]
        except KeyError as error:
            raise CollectorRegistrationError(f"未知或禁用的采集器：{pluginId}") from error

    def select(self, collectorIds: Iterable[str] | None = None) -> list[ValuationCollector]:
        """返回全部或指定已启用采集器，且顺序与注册顺序一致。"""
        if collectorIds is None:
            return list(self._collectors.values())
        return [self.get(collectorId) for collectorId in collectorIds]

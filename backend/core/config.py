"""Gestión de configuración de la aplicación y carga segura de credenciales desde .env."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import dotenv_values

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent
DEFAULT_ENV_PATH: Path = PROJECT_ROOT / ".env"
DEFAULT_OUTPUT_DIR: Path = PROJECT_ROOT / "salidas"
DEFAULT_USER_DATA_DIR: Path = PROJECT_ROOT / "user_data"
DEFAULT_FAVORITES_PATH: Path = PROJECT_ROOT / "favoritas.json"
DEFAULT_CLEANING_PROFILES_PATH: Path = PROJECT_ROOT / "perfiles_limpieza.json"


@dataclass(frozen=True)
class OracleConfig:
    """Objeto tipado de configuración para conexión a Oracle Database."""

    user: str = ""
    password: str = field(default="", repr=False)
    host: str = ""
    port: int = 1521
    service_name: str = ""
    dsn_override: str = ""
    env_file_exists: bool = False
    missing_vars: list[str] = field(default_factory=list)
    invalid_vars: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"OracleConfig(host={self.display_host!r}, port={self.port}, "
            f"service={self.display_service!r}, is_valid={self.is_valid}, "
            f"missing_vars={self.missing_vars})"
        )

    def __str__(self) -> str:
        return self.__repr__()

    @property
    def is_valid(self) -> bool:
        """Indica si todas las variables necesarias están presentes y son válidas."""
        return self.env_file_exists and len(self.missing_vars) == 0 and len(self.invalid_vars) == 0

    @property
    def effective_dsn(self) -> str:
        """Devuelve el DSN efectivo (ORACLE_DSN tiene prioridad sobre HOST/PORT/SERVICE_NAME)."""
        if self.dsn_override.strip():
            return self.dsn_override.strip()
        if self.host and self.service_name:
            return f"{self.host}:{self.port}/{self.service_name}"
        return ""

    @property
    def display_host(self) -> str:
        """Devuelve el host seguro para mostrar en la interfaz (sin usuario ni contraseña)."""
        if self.dsn_override.strip():
            dsn_clean = self._strip_credentials_from_dsn(self.dsn_override.strip())
            if "/" in dsn_clean:
                host_part = dsn_clean.split("/", 1)[0]
                return host_part
            return dsn_clean
        return self.host or "No configurado"

    @property
    def display_service(self) -> str:
        """Devuelve el nombre del servicio seguro para mostrar en la interfaz."""
        if self.dsn_override.strip():
            dsn_clean = self._strip_credentials_from_dsn(self.dsn_override.strip())
            if "/" in dsn_clean:
                return dsn_clean.split("/", 1)[1]
            return "DSN personalizado"
        return self.service_name or "No configurado"

    @property
    def status_message_es(self) -> str:
        """Mensaje descriptivo en español sobre el estado de la configuración .env."""
        if not self.env_file_exists:
            faltantes = ", ".join(self.missing_vars)
            return (
                f"No se encontró el archivo .env en la raíz del proyecto. "
                f"Variables faltantes: {faltantes}. "
                f"Copia el archivo .env.example como .env en la raíz del proyecto y completa tus datos."
            )
        if self.missing_vars or self.invalid_vars:
            partes: list[str] = []
            if self.missing_vars:
                partes.append(f"Variables faltantes: {', '.join(self.missing_vars)}")
            if self.invalid_vars:
                partes.append(f"Variables inválidas: {', '.join(self.invalid_vars)}")
            detalle = ". ".join(partes)
            return (
                f"Configuración incompleta en el archivo .env ({detalle}). "
                f"Revisa .env.example como referencia para completar las variables requeridas."
            )
        return f"Configuración cargada desde .env ({self.display_host} / {self.display_service})."

    @staticmethod
    def _strip_credentials_from_dsn(dsn: str) -> str:
        """Elimina posibles credenciales embebidas del tipo usuario/clave@host:puerto/servicio."""
        if "@" in dsn:
            return dsn.split("@", 1)[1]
        return dsn


def load_oracle_config(
    env_path: Path | str | None = None,
    env_override: dict[str, str | None] | None = None,
) -> OracleConfig:
    """
    Carga y valida la configuración de Oracle desde el archivo .env.

    Si el archivo .env no existe o faltan variables, no lanza excepciones:
    devuelve un OracleConfig con `is_valid=False` y el listado exacto de `missing_vars`.
    """
    target_path = Path(env_path) if env_path is not None else DEFAULT_ENV_PATH

    if env_override is not None:
        raw_values = {k: (v or "") for k, v in env_override.items()}
        file_exists = True
    else:
        file_exists = target_path.is_file()
        if file_exists:
            loaded = dotenv_values(target_path, encoding="utf-8")
            raw_values = {k: (v or "").strip() for k, v in loaded.items() if k is not None}
        else:
            raw_values = {}

    if not file_exists:
        return OracleConfig(
            env_file_exists=False,
            missing_vars=[
                "ORACLE_USER",
                "ORACLE_PASSWORD",
                "ORACLE_HOST",
                "ORACLE_SERVICE_NAME",
            ],
        )

    user = raw_values.get("ORACLE_USER", "").strip()
    password = raw_values.get("ORACLE_PASSWORD", "").strip()
    host = raw_values.get("ORACLE_HOST", "").strip()
    port_str = raw_values.get("ORACLE_PORT", "1521").strip() or "1521"
    service_name = raw_values.get("ORACLE_SERVICE_NAME", "").strip()
    dsn_override = raw_values.get("ORACLE_DSN", "").strip()

    # Si ORACLE_DSN incluye credenciales por error (user/pass@host), limpiamos el DSN
    if "@" in dsn_override:
        dsn_override = OracleConfig._strip_credentials_from_dsn(dsn_override)

    missing: list[str] = []
    invalid: list[str] = []

    if not user:
        missing.append("ORACLE_USER")
    if not password:
        missing.append("ORACLE_PASSWORD")

    # ORACLE_DSN tiene prioridad sobre HOST/PORT/SERVICE_NAME
    if not dsn_override:
        if not host:
            missing.append("ORACLE_HOST")
        if not service_name:
            missing.append("ORACLE_SERVICE_NAME")

    port = 1521
    try:
        port = int(port_str)
        if not (1 <= port <= 65535):
            invalid.append("ORACLE_PORT")
            port = 1521
    except ValueError:
        invalid.append("ORACLE_PORT")

    return OracleConfig(
        user=user,
        password=password,
        host=host,
        port=port,
        service_name=service_name,
        dsn_override=dsn_override,
        env_file_exists=True,
        missing_vars=missing,
        invalid_vars=invalid,
    )


def sanitize_sensitive_text(text: str, config: OracleConfig | None = None) -> str:
    """
    Elimina contraseñas, usuarios y cadenas de conexión con credenciales de cualquier
    mensaje de log o error antes de mostrarlo al usuario o guardarlo.
    """
    if not text:
        return ""

    sanitized = str(text)

    if config is not None:
        if config.password and len(config.password) >= 2:
            sanitized = sanitized.replace(config.password, "[PROTEGIDO]")
        if config.user and len(config.user) >= 2:
            # Reemplazar patrones user/pass@ o menciones explícitas de usuario junto a credenciales
            sanitized = re.sub(
                re.escape(config.user) + r"\s*/\s*[^\s@]+@",
                "[USUARIO]/[PROTEGIDO]@",
                sanitized,
                flags=re.IGNORECASE,
            )

    # Sanitizar patrones genéricos de contraseñas o DSN con credenciales (ej. usuario/clave@host)
    sanitized = re.sub(
        r"(?i)(password|passwd|pwd|contraseña|clave)\s*[:=]\s*(['\"]?)[^'\"\s,;)]+\2",
        r"\1=[PROTEGIDO]",
        sanitized,
    )
    sanitized = re.sub(
        r"[A-Za-z0-9_.$#]+\s*/\s*[^\s/@]+@[A-Za-z0-9_.\-:]+",
        "[CREDENCIALES_PROTEGIDAS]@host",
        sanitized,
    )
    return sanitized


def ensure_output_dir(custom_dir: str | Path | None = None) -> Path:
    """Asegura que el directorio de salida exista y lo devuelve."""
    target = Path(custom_dir) if custom_dir and str(custom_dir).strip() else DEFAULT_OUTPUT_DIR
    target.mkdir(parents=True, exist_ok=True)
    return target


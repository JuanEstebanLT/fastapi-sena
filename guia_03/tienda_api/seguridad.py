"""Funciones de autenticacion, tokens JWT y autorizacion por roles."""

import os
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError


ALGORITMO_JWT = "HS256"
DURACION_TOKEN_MINUTOS = 30
VARIABLE_CLAVE_JWT = "JWT_SECRET_KEY"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Los hashes bcrypt son datos de demostracion, no secretos. Las contrasenas en
# texto plano no se guardan en esta estructura ni se entregan en respuestas.
usuarios: dict[str, dict[str, str]] = {
    "admin": {
        "usuario": "admin",
        "password_hash": "$2b$12$mq5CvlR8uMbD9Nc2qU9ziuhq.6gBlfA.fJchohAwLfhwtsSNNqzoO",
        "rol": "admin",
    },
    "ana": {
        "usuario": "ana",
        "password_hash": "$2b$12$17yLHfLPQdp4rnD81S.yB.BicQ/wO3dAjPHWVgSX69jeRoVc1vUQC",
        "rol": "cliente",
    },
}


def _obtener_clave_jwt() -> str:
    """Obtiene la clave de firma sin incluir secretos en el codigo fuente."""
    clave = os.getenv(VARIABLE_CLAVE_JWT)
    if not clave:
        raise RuntimeError(
            f"Debe configurar la variable de entorno {VARIABLE_CLAVE_JWT}."
        )
    return clave


def hashear_password(password: str) -> str:
    """Genera un hash bcrypt con una sal aleatoria."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_password(password: str, password_hash: str) -> bool:
    """Compara una contrasena con un hash bcrypt valido."""
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"), password_hash.encode("utf-8")
        )
    except (TypeError, ValueError):
        return False


def buscar_usuario(nombre_usuario: str) -> dict[str, str] | None:
    """Busca un usuario por su identificador en el almacen en memoria."""
    return usuarios.get(nombre_usuario)


def crear_token(
    identificacion: str, expira_en: timedelta | None = None
) -> str:
    """Crea un JWT HS256 para un usuario con expiracion de 30 minutos."""
    ahora = datetime.now(timezone.utc)
    duracion = (
        expira_en
        if expira_en is not None
        else timedelta(minutes=DURACION_TOKEN_MINUTOS)
    )
    contenido = {
        "sub": identificacion,
        "iat": ahora,
        "exp": ahora + duracion,
    }
    return jwt.encode(contenido, _obtener_clave_jwt(), algorithm=ALGORITMO_JWT)


def _error_credenciales() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )


def obtener_usuario_actual(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> dict[str, str]:
    """Valida firma, algoritmo, expiracion y usuario contenido en el JWT."""
    try:
        contenido: dict[str, Any] = jwt.decode(
            token,
            _obtener_clave_jwt(),
            algorithms=[ALGORITMO_JWT],
            options={"require": ["sub", "exp"]},
        )
        nombre_usuario = contenido.get("sub")
        if not isinstance(nombre_usuario, str):
            raise _error_credenciales()
    except InvalidTokenError as error:
        raise _error_credenciales() from error

    usuario = buscar_usuario(nombre_usuario)
    if usuario is None:
        raise _error_credenciales()
    return usuario


def requerir_admin(
    usuario_actual: Annotated[dict[str, str], Depends(obtener_usuario_actual)],
) -> dict[str, str]:
    """Autoriza exclusivamente usuarios con rol administrador."""
    if usuario_actual["rol"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere el rol administrador",
        )
    return usuario_actual

"""Endpoints de registro, inicio de sesion y perfil autenticado."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, ConfigDict, Field

from guia_03.tienda_api.seguridad import (
    buscar_usuario,
    crear_token,
    hashear_password,
    obtener_usuario_actual,
    usuarios,
    verificar_password,
)


router = APIRouter(prefix="/auth", tags=["Autenticacion"])


class TokenRespuesta(BaseModel):
    access_token: str
    token_type: str


class UsuarioPublico(BaseModel):
    usuario: str
    rol: str


class RegistroEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    usuario: str = Field(
        min_length=3,
        max_length=50,
        pattern=r"^[A-Za-z0-9_.-]+$",
    )
    password: str = Field(min_length=6, max_length=72)
    rol: Literal["cliente"] = "cliente"


@router.post("/login", response_model=TokenRespuesta)
def iniciar_sesion(
    formulario: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> TokenRespuesta:
    usuario = buscar_usuario(formulario.username)
    if usuario is None or not verificar_password(
        formulario.password, usuario["password_hash"]
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contrasena incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenRespuesta(
        access_token=crear_token(usuario["usuario"]), token_type="bearer"
    )


@router.post("/registro", response_model=UsuarioPublico, status_code=201)
def registrar_usuario(datos: RegistroEntrada) -> UsuarioPublico:
    if buscar_usuario(datos.usuario) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El nombre de usuario ya esta registrado",
        )

    nuevo_usuario = {
        "usuario": datos.usuario,
        "password_hash": hashear_password(datos.password),
        "rol": "cliente",
    }
    usuarios[datos.usuario] = nuevo_usuario
    return UsuarioPublico(usuario=datos.usuario, rol="cliente")


@router.get("/yo", response_model=UsuarioPublico)
def consultar_perfil(
    usuario_actual: Annotated[dict[str, str], Depends(obtener_usuario_actual)],
) -> UsuarioPublico:
    return UsuarioPublico(
        usuario=usuario_actual["usuario"], rol=usuario_actual["rol"]
    )

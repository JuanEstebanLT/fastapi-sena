"""CRUD de categorias con escritura autenticada y borrado administrativo."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from guia_03.tienda_api.seguridad import obtener_usuario_actual, requerir_admin


router = APIRouter(prefix="/categorias", tags=["Categorias"])


class CategoriaEntrada(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)


categorias = [
    {"id": 1, "nombre": "Perifericos"},
    {"id": 2, "nombre": "Pantallas"},
    {"id": 3, "nombre": "Audio"},
]


@router.get("")
def listar_categorias():
    return categorias


@router.get("/{categoria_id}")
def obtener_categoria(categoria_id: int):
    for categoria in categorias:
        if categoria["id"] == categoria_id:
            return categoria
    raise HTTPException(status_code=404, detail="Categoria no encontrada")


@router.post("", status_code=201)
def crear_categoria(
    datos: CategoriaEntrada,
    _usuario_actual: Annotated[dict[str, str], Depends(obtener_usuario_actual)],
):
    nuevo_id = max((categoria["id"] for categoria in categorias), default=0) + 1
    nueva = {"id": nuevo_id, "nombre": datos.nombre}
    categorias.append(nueva)
    return {"mensaje": "Categoria creada", "categoria": nueva}


@router.put("/{categoria_id}")
def actualizar_categoria(
    categoria_id: int,
    datos: CategoriaEntrada,
    _usuario_actual: Annotated[dict[str, str], Depends(obtener_usuario_actual)],
):
    for categoria in categorias:
        if categoria["id"] == categoria_id:
            categoria["nombre"] = datos.nombre
            return {"mensaje": "Categoria actualizada", "categoria": categoria}
    raise HTTPException(status_code=404, detail="Categoria no encontrada")


@router.delete("/{categoria_id}")
def eliminar_categoria(
    categoria_id: int,
    _administrador: Annotated[dict[str, str], Depends(requerir_admin)],
):
    for categoria in categorias:
        if categoria["id"] == categoria_id:
            categorias.remove(categoria)
            return {"mensaje": "Categoria eliminada", "categoria": categoria}
    raise HTTPException(status_code=404, detail="Categoria no encontrada")

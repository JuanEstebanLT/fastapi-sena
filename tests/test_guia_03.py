import os
from copy import deepcopy
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient


# Clave exclusiva de la suite local; no representa un secreto de produccion.
os.environ.setdefault(
    "JWT_SECRET_KEY", "clave-solo-para-pruebas-automatizadas-guia-03"
)

from guia_03.tienda_api.main import app
from guia_03.tienda_api.routers import categorias as mod_categorias
from guia_03.tienda_api.routers import productos as mod_productos
from guia_03.tienda_api.seguridad import crear_token, usuarios


client = TestClient(app)
PRODUCTO_VALIDO = {
    "nombre": "Webcam",
    "precio": 75000,
    "categoria": "Perifericos",
}


@pytest.fixture(autouse=True)
def restaurar_datos_en_memoria():
    productos_originales = deepcopy(mod_productos.productos)
    categorias_originales = deepcopy(mod_categorias.categorias)
    usuarios_originales = deepcopy(usuarios)
    yield
    mod_productos.productos[:] = productos_originales
    mod_categorias.categorias[:] = categorias_originales
    usuarios.clear()
    usuarios.update(usuarios_originales)


def iniciar_sesion(usuario: str, password: str) -> str:
    respuesta = client.post(
        "/auth/login", data={"username": usuario, "password": password}
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["token_type"] == "bearer"
    return respuesta.json()["access_token"]


def autorizacion(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_aplicacion_documentacion_y_esquema_oauth2():
    assert client.get("/").status_code == 200
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200
    esquema = client.get("/openapi.json").json()
    etiquetas = {
        etiqueta
        for metodos in esquema["paths"].values()
        for operacion in metodos.values()
        for etiqueta in operacion.get("tags", [])
    }
    assert {"Autenticacion", "Productos", "Categorias"}.issubset(etiquetas)
    oauth2 = esquema["components"]["securitySchemes"]["OAuth2PasswordBearer"]
    assert oauth2["flows"]["password"]["tokenUrl"] == "/auth/login"


def test_consultas_get_de_productos_y_categorias_son_publicas():
    assert client.get("/productos").status_code == 200
    assert client.get("/productos/1").status_code == 200
    assert client.get("/categorias").status_code == 200
    assert client.get("/categorias/1").status_code == 200


def test_login_de_administrador_y_cliente():
    assert iniciar_sesion("admin", "admin123")
    assert iniciar_sesion("ana", "ana123")


def test_login_rechaza_credenciales_incorrectas():
    respuesta = client.post(
        "/auth/login", data={"username": "admin", "password": "incorrecta"}
    )
    assert respuesta.status_code == 401
    assert "password" not in respuesta.json()


def test_auth_yo_acepta_jwt_valido_y_no_revela_hash():
    token = iniciar_sesion("ana", "ana123")
    respuesta = client.get("/auth/yo", headers=autorizacion(token))
    assert respuesta.status_code == 200
    assert respuesta.json() == {"usuario": "ana", "rol": "cliente"}


def test_auth_yo_rechaza_token_ausente_invalido_y_alterado():
    assert client.get("/auth/yo").status_code == 401
    assert client.get(
        "/auth/yo", headers=autorizacion("token-invalido")
    ).status_code == 401

    token = iniciar_sesion("ana", "ana123")
    encabezado, contenido, firma = token.split(".")
    firma_alterada = ("A" if firma[0] != "A" else "B") + firma[1:]
    token_alterado = ".".join((encabezado, contenido, firma_alterada))
    assert client.get(
        "/auth/yo", headers=autorizacion(token_alterado)
    ).status_code == 401


def test_auth_yo_rechaza_token_expirado():
    token = crear_token("ana", expira_en=timedelta(seconds=-1))
    assert client.get("/auth/yo", headers=autorizacion(token)).status_code == 401


def test_productos_post_sin_token_devuelve_401():
    assert client.post("/productos", json=PRODUCTO_VALIDO).status_code == 401


def test_cliente_crea_y_actualiza_producto_con_autoria():
    headers = autorizacion(iniciar_sesion("ana", "ana123"))
    respuesta = client.post("/productos", json=PRODUCTO_VALIDO, headers=headers)
    assert respuesta.status_code == 201
    producto = respuesta.json()["producto"]
    assert producto["creado_por"] == "ana"

    actualizado = {**PRODUCTO_VALIDO, "precio": 81000}
    respuesta = client.put(
        f"/productos/{producto['id']}", json=actualizado, headers=headers
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["producto"]["precio"] == 81000


def test_put_de_producto_requiere_autenticacion():
    assert client.put("/productos/1", json=PRODUCTO_VALIDO).status_code == 401


def test_delete_de_producto_aplica_roles():
    token_cliente = iniciar_sesion("ana", "ana123")
    assert client.delete(
        "/productos/1", headers=autorizacion(token_cliente)
    ).status_code == 403

    token_admin = iniciar_sesion("admin", "admin123")
    assert client.delete(
        "/productos/1", headers=autorizacion(token_admin)
    ).status_code == 200
    assert client.get("/productos/1").status_code == 404


def test_categorias_post_y_put_requieren_autenticacion():
    assert client.post("/categorias", json={"nombre": "Computadores"}).status_code == 401
    assert client.put("/categorias/1", json={"nombre": "Computadores"}).status_code == 401


def test_cliente_crea_y_actualiza_categoria():
    headers = autorizacion(iniciar_sesion("ana", "ana123"))
    respuesta = client.post(
        "/categorias", json={"nombre": "Computadores"}, headers=headers
    )
    assert respuesta.status_code == 201
    categoria_id = respuesta.json()["categoria"]["id"]
    respuesta = client.put(
        f"/categorias/{categoria_id}",
        json={"nombre": "Portatiles"},
        headers=headers,
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["categoria"]["nombre"] == "Portatiles"


def test_delete_de_categoria_aplica_roles():
    token_cliente = iniciar_sesion("ana", "ana123")
    assert client.delete(
        "/categorias/1", headers=autorizacion(token_cliente)
    ).status_code == 403

    token_admin = iniciar_sesion("admin", "admin123")
    assert client.delete(
        "/categorias/1", headers=autorizacion(token_admin)
    ).status_code == 200
    assert client.get("/categorias/1").status_code == 404


def test_registro_genera_hash_y_permite_login_sin_revelar_password():
    datos = {"usuario": "nuevo_cliente", "password": "segura123"}
    respuesta = client.post("/auth/registro", json=datos)
    assert respuesta.status_code == 201
    assert respuesta.json() == {"usuario": "nuevo_cliente", "rol": "cliente"}
    assert usuarios["nuevo_cliente"]["password_hash"].startswith("$2")
    assert usuarios["nuevo_cliente"]["password_hash"] != datos["password"]
    token = iniciar_sesion("nuevo_cliente", "segura123")
    assert client.get("/auth/yo", headers=autorizacion(token)).json()["rol"] == "cliente"


def test_registro_no_permite_rol_admin_ni_usuarios_duplicados():
    intento_admin = client.post(
        "/auth/registro",
        json={"usuario": "intruso", "password": "segura123", "rol": "admin"},
    )
    assert intento_admin.status_code == 422
    assert "intruso" not in usuarios

    duplicado = client.post(
        "/auth/registro", json={"usuario": "ana", "password": "segura123"}
    )
    assert duplicado.status_code == 409


def test_errores_404_y_validaciones_422_se_conservan():
    headers_cliente = autorizacion(iniciar_sesion("ana", "ana123"))
    headers_admin = autorizacion(iniciar_sesion("admin", "admin123"))

    assert client.get("/productos/999").status_code == 404
    assert client.get("/categorias/999").status_code == 404
    assert client.put(
        "/productos/999", json=PRODUCTO_VALIDO, headers=headers_cliente
    ).status_code == 404
    assert client.put(
        "/categorias/999", json={"nombre": "Otra"}, headers=headers_cliente
    ).status_code == 404
    assert client.delete(
        "/productos/999", headers=headers_admin
    ).status_code == 404
    assert client.delete(
        "/categorias/999", headers=headers_admin
    ).status_code == 404

    assert client.post(
        "/productos",
        json={"nombre": "Invalido", "categoria": "Perifericos"},
        headers=headers_cliente,
    ).status_code == 422
    assert client.post(
        "/productos", json={**PRODUCTO_VALIDO, "precio": 0}, headers=headers_cliente
    ).status_code == 422
    assert client.post(
        "/categorias", json={"nombre": []}, headers=headers_cliente
    ).status_code == 422

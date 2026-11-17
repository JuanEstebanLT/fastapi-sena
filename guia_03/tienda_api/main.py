"""Aplicacion principal de la Guia 3."""

from fastapi import FastAPI

from guia_03.tienda_api.routers import auth, categorias, productos


app = FastAPI(
    title="API segura de la Tienda",
    description="Guia 3: autenticacion OAuth2, JWT y autorizacion por roles.",
    version="3.0.0",
)

app.include_router(auth.router)
app.include_router(productos.router)
app.include_router(categorias.router)


@app.get("/", tags=["Inicio"])
def inicio():
    return {"mensaje": "API segura de la Tienda funcionando. Visita /docs"}

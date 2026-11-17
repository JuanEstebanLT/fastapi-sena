# Guía 3 — Autenticación, autorización y seguridad

Esta guía continúa la API de comercio electrónico de la Guía 2 en una aplicación independiente. Incorpora autenticación OAuth2 con contraseña, tokens JWT firmados, hashes bcrypt y autorización basada en los roles `cliente` y `admin`. Las Guías 1 y 2 no se modifican.

## Objetivos técnicos

- Autenticar usuarios mediante `OAuth2PasswordRequestForm`.
- Firmar tokens JWT con HS256 y una vigencia de 30 minutos.
- almacenar solamente hashes bcrypt de las contraseñas.
- Proteger las escrituras del catálogo y limitar los borrados al rol administrador.
- Mantener productos, categorías y usuarios temporalmente en memoria.
- Verificar el comportamiento mediante pytest y `TestClient`.

## Arquitectura

```text
guia_03/
├── __init__.py
├── README.md
└── tienda_api/
    ├── __init__.py
    ├── main.py
    ├── seguridad.py
    └── routers/
        ├── __init__.py
        ├── auth.py
        ├── productos.py
        └── categorias.py
```

`main.py` crea la aplicación y registra los tres routers. `seguridad.py` concentra bcrypt, JWT, el esquema OAuth2, los usuarios en memoria y las dependencias de autorización. Cada recurso conserva su propio `APIRouter`.

## Instalación

Desde la raíz del repositorio, en CMD o PowerShell:

```bat
py -m venv venv
venv\Scripts\activate.bat
python -m pip install -r requirements-dev.txt
```

Las dependencias nuevas de ejecución son `PyJWT`, `bcrypt` y `python-multipart`. Esta última permite que FastAPI procese el formulario OAuth2 del inicio de sesión.

## Clave JWT local

La aplicación lee obligatoriamente `JWT_SECRET_KEY` del entorno. El repositorio no contiene una clave de producción ni carga automáticamente archivos `.env`.

En CMD, para la sesión actual:

```bat
set JWT_SECRET_KEY=reemplace-esto-por-una-clave-local-larga-y-aleatoria
```

En PowerShell:

```powershell
$env:JWT_SECRET_KEY = "reemplace-esto-por-una-clave-local-larga-y-aleatoria"
```

También puede guardarse el comando localmente en un archivo `.env`, que ya está excluido por `.gitignore`, y cargarlo con la herramienta elegida por el desarrollador. No se debe versionar ese archivo. Para un entorno real se debe usar un gestor de secretos y una clave distinta.

## Ejecución

Con el entorno virtual activado, la variable configurada y desde la raíz:

```bat
python -m uvicorn guia_03.tienda_api.main:app --reload
```

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- OpenAPI: http://127.0.0.1:8000/openapi.json

## Mecanismos de seguridad

- **OAuth2 Password:** `/auth/login` recibe los campos de formulario `username` y `password`. El botón **Authorize** de Swagger utiliza este mismo flujo.
- **bcrypt:** las contraseñas se comparan con hashes que incorporan una sal. Los hashes nunca se exponen mediante endpoints.
- **JWT:** el token incluye el usuario en `sub`, la fecha de emisión en `iat` y una expiración `exp` de 30 minutos. Se acepta únicamente el algoritmo HS256 y se valida que el usuario todavía exista.
- **Roles:** cualquier usuario autenticado puede crear y actualizar. Solo `admin` puede eliminar. Un registro público siempre crea el rol `cliente`.

## Endpoints y permisos

| Método | Ruta | Permiso | Respuesta esperada |
|---|---|---|---|
| GET | `/` | Público | Bienvenida |
| POST | `/auth/login` | Público | Token bearer o 401 |
| POST | `/auth/registro` | Público | Cliente creado o error de validación |
| GET | `/auth/yo` | Token válido | Usuario y rol |
| GET | `/productos` | Público | Lista de productos |
| GET | `/productos/{producto_id}` | Público | Producto o 404 |
| POST | `/productos` | Token válido | 201 y `creado_por` |
| PUT | `/productos/{producto_id}` | Token válido | Producto actualizado o 404 |
| DELETE | `/productos/{producto_id}` | Administrador | Producto eliminado, 403 o 404 |
| GET | `/categorias` | Público | Lista de categorías |
| GET | `/categorias/{categoria_id}` | Público | Categoría o 404 |
| POST | `/categorias` | Token válido | Categoría creada |
| PUT | `/categorias/{categoria_id}` | Token válido | Categoría actualizada o 404 |
| DELETE | `/categorias/{categoria_id}` | Administrador | Categoría eliminada, 403 o 404 |

## Usuarios académicos locales

| Usuario | Contraseña de demostración | Rol |
|---|---|---|
| `admin` | `admin123` | `admin` |
| `ana` | `ana123` | `cliente` |

Estas cuentas sirven exclusivamente para prácticas locales. En la estructura en memoria solo se almacenan sus hashes bcrypt.

## Uso de Swagger UI

1. Abra `/docs` y compruebe primero los GET públicos.
2. Pulse **Authorize**.
3. Use `admin`/`admin123` o `ana`/`ana123`; deje `client_id` y `client_secret` vacíos.
4. Ejecute `/auth/yo` para verificar la identidad activa.
5. Pruebe POST y PUT con cualquiera de las dos cuentas.
6. Intente un DELETE con `ana` para observar el 403.
7. Cierre la autorización, vuelva a autorizar como `admin` y repita el DELETE para obtener 200.
8. Use `/auth/registro` sin enviar `rol`, inicie sesión con la cuenta creada y confirme que `/auth/yo` muestra `cliente`.

## Pruebas automatizadas

La suite configura una clave exclusiva de pruebas y restaura las listas y usuarios después de cada caso:

```bat
python -m pytest tests/test_guia_03.py -q
python -m pytest tests -q
```

La segunda orden valida conjuntamente las Guías 1, 2 y 3.

## Limitaciones y estado

- Todos los datos están en memoria y se pierden al reiniciar el proceso.
- No hay base de datos, revocación de tokens, recuperación de contraseña ni despliegue productivo.
- La implementación técnica y sus pruebas automatizadas forman solo una fase de la actividad.
- Las capturas manuales, el informe académico, las evidencias publicadas y la sustentación continúan pendientes y deben elaborarse a partir de ejecuciones reales.

"""Production ASGI entrypoint.

Keeping the eager application object here lets imports of ``app.main`` remain
side-effect free for evaluators and tests. Uvicorn imports this module only
when it is actually starting a backend process.
"""

from app.main import create_app


app = create_app()

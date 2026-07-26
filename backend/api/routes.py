from backend.api.upload import router as upload_router
from backend.api.status import router as status_router
from backend.api.dashboard import router as dashboard_router
from backend.api.extract   import router as extract_router 



# def register_routes(app):
#     """Register all API routers with the FastAPI app."""
#     try:
#         from backend.api.upload import router as upload_router
#         app.include_router(upload_router, prefix="/api/v1")
#         print("✅ Upload router registered")
#     except Exception as e:
#         print(f"❌ Upload router failed: {e}")

#     try:
#         from backend.api.status import router as status_router
#         app.include_router(status_router, prefix="/api/v1")
#         print("✅ Status router registered")
#     except Exception as e:
#         print(f"❌ Status router failed: {e}")

#     try:
#         from backend.api.dashboard import router as dashboard_router
#         app.include_router(dashboard_router, prefix="/api/v1")
#         print("✅ Dashboard router registered")
#     except Exception as e:
#         print(f"❌ Dashboard router failed: {e}")
def register_routes(app):
    """Register all API routers with the FastAPI app."""
    app.include_router(upload_router, prefix="/api/v1")
    app.include_router(status_router, prefix="/api/v1")
    app.include_router(dashboard_router, prefix="/api/v1")
    app.include_router(extract_router,   prefix="/api/v1")   # ← ADD THIS LINE
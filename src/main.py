from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.routers.invoices import router as invoices_router
from src.routers.policy import router as policy_router
from src.service.invoice_service import InvoiceService
from src.service.temp_storage import clear_content_hash_dir, clear_invoice_temp_dir

load_dotenv()


def _cors_origins() -> list[str]:
    return [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Wipe temp dirs and attach a fresh InvoiceService."""
    clear_invoice_temp_dir()
    clear_content_hash_dir()
    app.state.invoice_service = InvoiceService()
    yield


app = FastAPI(title="KPN Invoice Processing", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(invoices_router)
app.include_router(policy_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=False)

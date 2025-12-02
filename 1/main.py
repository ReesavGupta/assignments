from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status, Query, Path, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
import time
from typing import List, Optional
from database import async_engine, init_db, get_session
import crud, schemas, auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables
    await init_db()
    yield
    # Shutdown: nothing specific needed for now


app = FastAPI(title="Assignments API - FastAPI Fundamentals", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.middleware("http")
async def timing_middleware(request, call_next):
    """Middleware that logs request processing time and adds a header."""
    start = time.time()
    # pre-request logic
    print(f"Incoming request: {request.method} {request.url}")
    response = await call_next(request)
    # post-request logic
    process_time = time.time() - start
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Custom-Header"] = "AssignmentsApp"
    print(f"Completed in {process_time:.4f}s -> status {response.status_code}")
    return response


# Authentication routes
@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    token = await auth.authenticate_user_and_get_token(form_data.username, form_data.password)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return {"access_token": token, "token_type": "bearer"}


@app.get("/protected")
async def protected_route(current_user: schemas.UserOut = Depends(auth.get_current_user)):
    return {"msg": f"Hello, {current_user.username}. You accessed a protected route."}


# Item CRUD + list with pagination, sorting and search
@app.post("/items/", response_model=schemas.ItemOut)
async def create_item(item_in: schemas.ItemCreate, db=Depends(get_session), current_user: schemas.UserOut = Depends(auth.get_current_user)):
    item = await crud.create_item(db, item_in, owner_username=current_user.username)
    return item


@app.get("/items/", response_model=schemas.ItemList)
async def list_items(
    q: Optional[str] = Query(None, description="Search term (in title or description)"),
    limit: int = Query(10, gt=0, le=100),
    offset: int = Query(0, ge=0),
    sort_by: Optional[str] = Query("id", description="Field to sort by"),
    order: Optional[str] = Query("asc", regex="^(asc|desc)$"),
    db=Depends(get_session),
):
    items, total = await crud.get_items(
        db,
        q=q,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        order=order,
    )
    # Convert ORM items into Pydantic models for type safety
    items_out = [schemas.ItemOut.model_validate(item) for item in items]
    return schemas.ItemList(items=items_out, total=total, limit=limit, offset=offset)


@app.get("/items/{item_id}", response_model=schemas.ItemOut)
async def get_item(item_id: int = Path(..., gt=0), db=Depends(get_session)):
    item = await crud.get_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.put("/items/{item_id}", response_model=schemas.ItemOut)
async def update_item(item_id: int, item_in: schemas.ItemUpdate, db=Depends(get_session), current_user: schemas.UserOut = Depends(auth.get_current_user)):
    item = await crud.update_item(db, item_id, item_in, current_user.username)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found or not owned by you")
    return item


@app.delete("/items/{item_id}")
async def delete_item(item_id: int, db=Depends(get_session), current_user: schemas.UserOut = Depends(auth.get_current_user)):
    ok = await crud.delete_item(db, item_id, current_user.username)
    if not ok:
        raise HTTPException(status_code=404, detail="Item not found or not owned by you")
    return JSONResponse({"ok": True})


@app.get("/users/me", response_model=schemas.UserOut)
async def read_users_me(current_user: schemas.UserOut = Depends(auth.get_current_user)):
    return current_user


@app.post("/users/", response_model=schemas.UserOut)
async def create_user(user_in: schemas.UserCreate, db=Depends(get_session)):
    user = await crud.create_user(db, user_in)
    return user


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, log_level="info")
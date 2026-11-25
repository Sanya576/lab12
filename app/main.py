import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import sessionmaker, declarative_base, Session

# Настройка подключения к БД
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/app_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Модель таблицы в PostgreSQL
class ItemDB(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    price = Column(Float, nullable=False)

# Создаем таблицы при старте
Base.metadata.create_all(bind=engine)

# Схемы Pydantic для валидации входящих/исходящих данных
class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Название товара")
    description: Optional[str] = Field(None, max_length=255)
    price: float = Field(..., gt=0, description="Цена должна быть больше 0")

class ItemResponse(ItemCreate):
    id: int

    class Config:
        from_attributes = True

app = FastAPI(title="Simple Python Microservice")

# Зависимость для получения сессии БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 1. GET — получить список всех записей
@app.get("/items", response_model=List[ItemResponse])
def get_items(db: Session = Depends(get_db)):
    return db.query(ItemDB).all()

# 2. GET — получить одну запись по ID
@app.get("/items/{item_id}", response_model=ItemResponse)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(ItemDB).filter(ItemDB.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Элемент с id={item_id} не найден"
        )
    return item

# 3. POST — создать новую запись
@app.post("/items", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    db_item = ItemDB(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

# 4. PUT — обновить существующую запись
@app.put("/items/{item_id}", response_model=ItemResponse)
def update_item(item_id: int, updated_item: ItemCreate, db: Session = Depends(get_db)):
    db_item = db.query(ItemDB).filter(ItemDB.id == item_id).first()
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Элемент с id={item_id} не найден"
        )
    for key, value in updated_item.model_dump().items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item

# 5. DELETE — удалить запись
@app.delete("/items/{item_id}", status_code=status.HTTP_200_OK)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    db_item = db.query(ItemDB).filter(ItemDB.id == item_id).first()
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Элемент с id={item_id} не найден"
        )
    db.delete(db_item)
    db.commit()
    return {"message": f"Элемент с id={item_id} успешно удален"}
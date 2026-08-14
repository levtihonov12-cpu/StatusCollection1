from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from database import engine, get_db
import models
import schemas

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Status Collection API")


@app.get("/")
def root():
    return {
        "status": "Status Collection API работает"
    }


@app.get("/api/categories", response_model=List[schemas.Category])
def get_categories(db: Session = Depends(get_db)):
    return db.query(models.Category).all()


@app.get("/api/products", response_model=List[schemas.Product])
def get_products(
    category_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Product).filter(
        models.Product.is_available.is_(True)
    )

    if category_id is not None:
        query = query.filter(
            models.Product.category_id == category_id
        )

    return query.all()


@app.get("/api/products/{product_id}", response_model=schemas.Product)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(
        models.Product.id == product_id
    ).first()

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Товар не найден"
        )

    return product

@app.post("/api/users/register", response_model=schemas.User)
def register_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(
        models.User.telegram_id == payload.telegram_id
    ).first()

    if user is None:
        user = models.User(**payload.model_dump())
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.username = payload.username or user.username
        user.first_name = payload.first_name or user.first_name
        user.last_name = payload.last_name or user.last_name
        db.commit()
        db.refresh(user)

    return user


@app.post("/api/orders", response_model=schemas.OrderOut)
def create_order(payload: schemas.OrderCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(
        models.User.telegram_id == payload.telegram_id
    ).first()

    if user is None:
        user = models.User(telegram_id=payload.telegram_id)
        db.add(user)
        db.commit()
        db.refresh(user)

    if not payload.items:
        raise HTTPException(status_code=400, detail="Корзина пуста")

    order = models.Order(
        user_id=user.id,
        customer_name=payload.customer_name,
        phone=payload.phone,
        address=payload.address,
        comment=payload.comment,
        status="new",
        total_price=0
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    total = 0

    for item in payload.items:
        product = db.query(models.Product).filter(
            models.Product.id == item.product_id
        ).first()

        if product is None:
            raise HTTPException(status_code=404, detail="Товар не найден")

        total += product.price * item.quantity

        db.add(models.OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=item.quantity,
            price=product.price
        ))

    order.total_price = total
    db.commit()
    db.refresh(order)

    return order


@app.get("/api/orders", response_model=List[schemas.OrderOut])
def get_orders(telegram_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(
        models.User.telegram_id == telegram_id
    ).first()

    if user is None:
        return []

    orders = db.query(models.Order).filter(
        models.Order.user_id == user.id
    ).order_by(models.Order.id.desc()).all()

    return orders

@app.post("/api/products", response_model=schemas.Product)
def create_product(payload: schemas.ProductCreate, db: Session = Depends(get_db)):
    category = db.query(models.Category).filter(
        models.Category.id == payload.category_id
    ).first()

    if category is None:
        raise HTTPException(status_code=404, detail="Категория не найдена")

    product = models.Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@app.delete("/api/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(
        models.Product.id == product_id
    ).first()

    if product is None:
        raise HTTPException(status_code=404, detail="Товар не найден")

    db.delete(product)
    db.commit()
    return {"status": "deleted"}


@app.get("/api/orders/all", response_model=List[schemas.OrderOut])
def get_all_orders(db: Session = Depends(get_db)):
    return db.query(models.Order).order_by(models.Order.id.desc()).all()


@app.post("/api/orders/{order_id}/status")
def update_order_status(
    order_id: int,
    payload: schemas.OrderStatusUpdate,
    db: Session = Depends(get_db)
):
    order = db.query(models.Order).filter(
        models.Order.id == order_id
    ).first()

    if order is None:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    order.status = payload.status
    db.commit()

    return {
        "status": "updated",
        "order_id": order_id,
        "new_status": payload.status
    }
import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import Product as ProductSchema, BlogPost as BlogPostSchema, Consultation as ConsultationSchema, Order as OrderSchema

app = FastAPI(title="E-commerce + Blog + Consultation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Backend running", "services": ["products", "blogs", "consultations", "checkout"]}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

# ---------------- Products ----------------

class SeedRequest(BaseModel):
    force: bool = False

SAMPLE_PRODUCTS: List[dict] = [
    {
        "title": f"Product {i+1}",
        "description": "A great product you will love.",
        "price": float(499 + i * 50),
        "category": "general",
        "in_stock": True,
        "image": f"https://picsum.photos/seed/p{i}/600/400",
        "sku": f"SKU{i+1:03}",
        "stock_qty": 20
    }
    for i in range(10)
]

@app.post("/api/products/seed")
def seed_products(body: SeedRequest):
    existing = db["product"].count_documents({}) if db else 0
    if existing > 0 and not body.force:
        return {"inserted": 0, "message": "Products already exist"}
    if body.force:
        db["product"].delete_many({})
    inserted = 0
    for p in SAMPLE_PRODUCTS:
        create_document("product", p)
        inserted += 1
    return {"inserted": inserted}

@app.get("/api/products")
def list_products():
    docs = get_documents("product")
    # Convert ObjectId to str if present
    for d in docs:
        if "_id" in d:
            d["id"] = str(d.pop("_id"))
    return {"items": docs}

# ---------------- Blogs ----------------

class BlogCreate(BaseModel):
    title: str
    slug: str
    content: str
    excerpt: Optional[str] = None
    cover_image: Optional[str] = None
    author: Optional[str] = None

@app.get("/api/blogs")
def list_blogs():
    docs = get_documents("blogpost")
    for d in docs:
        if "_id" in d:
            d["id"] = str(d.pop("_id"))
    return {"items": docs}

@app.post("/api/blogs")
def create_blog(blog: BlogCreate):
    # Prevent duplicate slug
    exists = db["blogpost"].find_one({"slug": blog.slug})
    if exists:
        raise HTTPException(status_code=400, detail="Slug already exists")
    bid = create_document("blogpost", blog.model_dump())
    return {"id": bid}

@app.get("/api/blogs/{slug}")
def get_blog(slug: str):
    doc = db["blogpost"].find_one({"slug": slug})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    doc["id"] = str(doc.pop("_id"))
    return doc

# ---------------- Consultations ----------------

class ConsultationRequest(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    doctor: str
    date: str
    time: str
    notes: Optional[str] = None

@app.post("/api/consultations")
def book_consultation(req: ConsultationRequest):
    cid = create_document("consultation", req.model_dump())
    return {"id": cid, "status": "pending"}

@app.get("/api/consultations")
def list_consultations(limit: int = 20):
    docs = get_documents("consultation", {}, limit)
    for d in docs:
        if "_id" in d:
            d["id"] = str(d.pop("_id"))
    return {"items": docs}

# ---------------- Checkout / Orders ----------------

class OrderItemIn(BaseModel):
    product_id: str
    title: str
    price: float
    quantity: int
    image: Optional[str] = None

class CreateOrderRequest(BaseModel):
    items: List[OrderItemIn]
    customer_name: str
    customer_email: str
    customer_address: str

@app.post("/api/checkout/create-order")
def create_order(req: CreateOrderRequest):
    if not req.items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    subtotal = sum(i.price * i.quantity for i in req.items)
    tax = round(subtotal * 0.18, 2)  # 18% GST example
    shipping = 49.0 if subtotal < 999 else 0.0
    total = round(subtotal + tax + shipping, 2)

    order_doc = {
        "items": [i.model_dump() for i in req.items],
        "subtotal": subtotal,
        "tax": tax,
        "shipping": shipping,
        "total": total,
        "currency": "INR",
        "customer_name": req.customer_name,
        "customer_email": req.customer_email,
        "customer_address": req.customer_address,
        "payment_status": "pending",
        "payment_provider": "mock"
    }
    oid = create_document("order", order_doc)

    # Mock payment URL (would be Razorpay/Stripe in real app)
    payment_url = f"/api/checkout/confirm?order_id={oid}&status=paid"
    return {"order_id": oid, "amount": total, "currency": "INR", "payment_url": payment_url}

class ConfirmRequest(BaseModel):
    order_id: str
    status: str  # "paid" | "failed"

@app.post("/api/checkout/confirm")
@app.get("/api/checkout/confirm")
def confirm_order(order_id: Optional[str] = None, status: Optional[str] = None):
    # Support GET with query params and POST JSON
    from fastapi import Request
    # If used as POST, read from body via dependency is complex; keep simple
    if order_id is None:
      # try read from environment? keep as is for GET usage from frontend redirect
      raise HTTPException(status_code=400, detail="order_id required")
    order = db["order"].find_one({"_id": __import__("bson").ObjectId(order_id)}) if order_id else None
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    new_status = "paid" if status == "paid" else "failed"
    db["order"].update_one({"_id": __import__("bson").ObjectId(order_id)}, {"$set": {"payment_status": new_status}})
    return {"order_id": order_id, "payment_status": new_status}

@app.get("/api/orders")
def list_orders(limit: int = 20):
    docs = get_documents("order", {}, limit)
    for d in docs:
        if "_id" in d:
            d["id"] = str(d.pop("_id"))
    return {"items": docs}

# ------------- Schema viewer support -------------

@app.get("/schema")
def get_schema_info():
    # Minimal schema endpoint so external tools can infer collections
    return {
        "collections": ["user", "product", "blogpost", "consultation", "order"],
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

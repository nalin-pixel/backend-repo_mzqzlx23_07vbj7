"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogpost" collection
- Consultation -> "consultation" collection
- Order -> "order" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List

# Core schemas

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: Optional[str] = Field(None, description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in currency units")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")
    image: Optional[str] = Field(None, description="Product image URL")
    sku: Optional[str] = Field(None, description="Stock keeping unit")
    stock_qty: Optional[int] = Field(10, ge=0, description="Available quantity")

class BlogPost(BaseModel):
    """Simple blog post schema"""
    title: str
    slug: str
    excerpt: Optional[str] = None
    content: str
    cover_image: Optional[str] = None
    author: Optional[str] = None

class Consultation(BaseModel):
    """Doctor consultation booking"""
    name: str
    email: str
    phone: Optional[str] = None
    doctor: str
    date: str  # ISO date string
    time: str  # HH:MM
    notes: Optional[str] = None
    status: str = Field("pending", description="pending | confirmed | completed | cancelled")

class OrderItem(BaseModel):
    product_id: str
    title: str
    price: float
    quantity: int
    image: Optional[str] = None

class Order(BaseModel):
    """Customer order"""
    items: List[OrderItem]
    subtotal: float
    tax: float
    shipping: float
    total: float
    currency: str = "INR"
    customer_name: str
    customer_email: str
    customer_address: str
    payment_status: str = Field("pending", description="pending | paid | failed")
    payment_provider: str = Field("mock", description="mock | stripe | razorpay etc")

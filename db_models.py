from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    address_id = Column(String, ForeignKey('addresses.id'), nullable=True)

    address = relationship('Address', back_populates='user')
    orders = relationship('Order', back_populates='user')


class Address(Base):
    __tablename__ = 'addresses'
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'), nullable=True)
    line1 = Column(String, nullable=False)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    country = Column(String, nullable=True)
    postal_code = Column(String, nullable=True)

    user = relationship('User', back_populates='address')
    orders = relationship('Order', back_populates='shipping_address')


class Order(Base):
    __tablename__ = 'orders'
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    status = Column(String, nullable=False)
    total_amount = Column(Float, nullable=True)
    shipping_address_id = Column(String, ForeignKey('addresses.id'), nullable=True)
    placed_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship('User', back_populates='orders')
    shipping_address = relationship('Address', back_populates='orders')
    items = relationship('OrderItem', back_populates='order')


class OrderItem(Base):
    __tablename__ = 'order_items'
    id = Column(String, primary_key=True)
    order_id = Column(String, ForeignKey('orders.id'), nullable=False)
    product_id = Column(String, ForeignKey('products.id'), nullable=True)
    product_name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=True)

    order = relationship('Order', back_populates='items')


class Product(Base):
    __tablename__ = 'products'
    id = Column(String, primary_key=True)
    sku = Column(String, unique=True, nullable=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=True)
    available_qty = Column(Integer, nullable=True)
    metadata = Column(Text, nullable=True)


class Coupon(Base):
    __tablename__ = 'coupons'
    code = Column(String, primary_key=True)
    discount_type = Column(String, nullable=False)  # 'percent' or 'fixed'
    discount_value = Column(Float, nullable=False)
    expiry_date = Column(String, nullable=True)
    usage_limit = Column(Integer, nullable=True)
    active = Column(Boolean, default=True)


class UserCoupon(Base):
    __tablename__ = 'user_coupons'
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    coupon_code = Column(String, ForeignKey('coupons.code'), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    redeemed_at = Column(DateTime, nullable=True)


class Session(Base):
    __tablename__ = 'sessions'
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'), nullable=True)
    session_token = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)


__all__ = [
    'Base', 'User', 'Address', 'Order', 'OrderItem', 'Product', 'Coupon', 'UserCoupon', 'Session'
]

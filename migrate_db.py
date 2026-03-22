"""Create SQLite DB, tables and seed initial data from existing in-memory data."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import uuid
from db_models import Base, User, Address, Order, OrderItem, Product, Coupon, UserCoupon, Session as AppSession

# Use a local SQLite file for simplicity. In production use Cloud SQL.
ENGINE = create_engine('sqlite:///app.db', echo=False, future=True)


def mkid(prefix: str = 'id') -> str:
    return prefix + str(uuid.uuid4())[:8]


def seed(engine):
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        # Skip seeding if users already exist
        if session.query(User).first():
            print('DB already seeded.')
            return

        # Users
        u1 = User(id='u1', name='John Doe', email='john@example.com')
        u2 = User(id='u2', name='Alice Smith', email='alice@example.com')
        session.add_all([u1, u2])

        # Addresses
        a1 = Address(id='a_u1', user_id='u1', line1='Kochi, Kerala', city='Kochi', country='India', postal_code='')
        a2 = Address(id='a_u2', user_id='u2', line1='Bangalore, India', city='Bangalore', country='India', postal_code='')
        session.add_all([a1, a2])

        # Orders
        o1 = Order(id='12345', user_id='u1', status='Shipped', shipping_address_id='a_u1', placed_at=None)
        o2 = Order(id='10234', user_id='u1', status='Processing', shipping_address_id='a_u1', placed_at=None)
        o3 = Order(id='20001', user_id='u2', status='Delivered', shipping_address_id='a_u2', placed_at=None)
        o4 = Order(id='30001', user_id='u2', status='Cancelled', shipping_address_id='a_u2', placed_at=None)
        session.add_all([o1, o2, o3, o4])

        # Order items
        oi1 = OrderItem(id='i1', order_id='12345', product_name='Running Shoes', quantity=1, unit_price=59.99)
        oi2 = OrderItem(id='i2', order_id='12345', product_name='T-shirt', quantity=2, unit_price=19.99)
        oi3 = OrderItem(id='i3', order_id='10234', product_name='Laptop', quantity=1, unit_price=999.0)
        oi4 = OrderItem(id='i4', order_id='20001', product_name='Headphones', quantity=1, unit_price=89.0)
        oi5 = OrderItem(id='i5', order_id='30001', product_name='Backpack', quantity=1, unit_price=49.0)
        session.add_all([oi1, oi2, oi3, oi4, oi5])

        # Products (minimal)
        p1 = Product(id='p_running', sku='RUN-001', name='Running Shoes', price=59.99, available_qty=50)
        p2 = Product(id='p_tshirt', sku='TS-001', name='T-shirt', price=19.99, available_qty=200)
        session.add_all([p1, p2])

        # Coupons
        c1 = Coupon(code='SAVE20', discount_type='percent', discount_value=20.0, expiry_date='2026-04-01', usage_limit=None, active=True)
        c2 = Coupon(code='FESTIVE10', discount_type='percent', discount_value=10.0, expiry_date='2026-03-30', usage_limit=None, active=True)
        c3 = Coupon(code='WELCOME5', discount_type='percent', discount_value=5.0, expiry_date='2026-05-01', usage_limit=None, active=True)
        session.add_all([c1, c2, c3])

        # Assign user coupons
        uc1 = UserCoupon(id='uc1', user_id='u1', coupon_code='SAVE20')
        uc2 = UserCoupon(id='uc2', user_id='u1', coupon_code='FESTIVE10')
        uc3 = UserCoupon(id='uc3', user_id='u2', coupon_code='WELCOME5')
        session.add_all([uc1, uc2, uc3])

        # Commit
        session.commit()
        print('Seed complete.')


if __name__ == '__main__':
    seed(ENGINE)

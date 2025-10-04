"""
Product stocks (write-only model)
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""
from sqlalchemy import text

from stocks.models.product import Product
from stocks.models.stock import Stock
from db import get_redis_conn, get_sqlalchemy_session

def set_stock_for_product(product_id, quantity):
    """Set stock quantity for product in MySQL"""
    session = get_sqlalchemy_session()
    try: 
        result = session.execute(
            text(f"""
                UPDATE stocks 
                SET quantity = :qty 
                WHERE product_id = :pid
            """),
            {"pid": product_id, "qty": quantity}
        )
        response_message = f"rows updated: {result.rowcount}"
        if result.rowcount == 0:
            new_stock = Stock(product_id=product_id, quantity=quantity)
            session.add(new_stock)
            session.flush() 
            session.commit()
            response_message = f"rows added: {new_stock.product_id}"
  
        r = get_redis_conn()
        r.hset(f"stock:{product_id}", "quantity", quantity)
        return response_message
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
    
def update_stock_mysql(session, order_items, operation):
    """ Update stock quantities in MySQL according to a given operation (+/-) """
    try:
        for item in order_items:
            if hasattr(order_items[0], 'product_id'):
                pid = item.product_id
                qty = item.quantity
            else:
                pid = item['product_id']
                qty = item['quantity']
            session.execute(
                text(f"""
                    UPDATE stocks 
                    SET quantity = quantity {operation} :qty 
                    WHERE product_id = :pid
                """),
                {"pid": pid, "qty": qty}
            )
    except Exception as e:
        raise e
    
def check_out_items_from_stock(session, order_items):
    """ Decrease stock quantities in Redis """
    update_stock_mysql(session, order_items, "-")
    
def check_in_items_to_stock(session, order_items):
    """ Increase stock quantities in Redis """
    update_stock_mysql(session, order_items, "+")

def update_stock_redis(order_items, operation):
    """ Update stock quantities and product information in Redis """
    if not order_items:
        return
    r = get_redis_conn()
    stock_keys = list(r.scan_iter("stock:*"))
    session = get_sqlalchemy_session()
    try:
        if stock_keys:
            pipeline = r.pipeline()
            for item in order_items:
                if hasattr(item, 'product_id'):
                    product_id = item.product_id
                    quantity = item.quantity
                else:
                    product_id = item['product_id']
                    quantity = item['quantity']

                # Récupérer les infos produit
                product = session.query(Product).filter_by(id=product_id).first()
                current_stock = r.hget(f"stock:{product_id}", "quantity")
                current_stock = int(current_stock) if current_stock else 0

                if operation == '+':
                    new_quantity = current_stock + quantity
                else:
                    new_quantity = current_stock - quantity

                # Ajout des infos supplémentaires dans Redis
                pipeline.hset(
                    f"stock:{product_id}",
                    mapping={
                        "quantity": new_quantity,
                        "name": product.name if product else "",
                        "sku": product.sku if product else "",
                        "price": float(product.price) if product else 0.0
                    }
                )
            pipeline.execute()
        else:
            _populate_redis_from_mysql(r)
    finally:
        session.close()

def _populate_redis_from_mysql(redis_conn):
    """ Helper function to populate Redis from MySQL stocks table """
    session = get_sqlalchemy_session()
    try:
        stocks = session.execute(
            text('''
                 SELECT product_id, quantity, name, sku, price FROM stocks
                     JOIN products ON stocks.product_id = products.id
            ''')
        ).fetchall()

        if not len(stocks):
            print("Il n'est pas nécessaire de synchronisér le stock MySQL avec Redis")
            return
        
        pipeline = redis_conn.pipeline()
        
        for product_id, quantity, name, sku, price in stocks:
            pipeline.hset(
                f"stock:{product_id}", 
                mapping={
                    "quantity": quantity,
                    "name": name,
                    "sku": sku,
                    "price": float(price)
                }
            )
        
        pipeline.execute()
        print(f"{len(stocks)} enregistrements de stock ont été synchronisés avec Redis")
        
    except Exception as e:
        print(f"Erreur de synchronisation: {e}")
        raise e
    finally:
        session.close()
"""
Tests for orders manager
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""

import json
import pytest
from store_manager import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health(client):
    result = client.get('/health-check')
    assert result.status_code == 200
    assert result.get_json() == {'status':'ok'}

def test_stock_flow(client):
    # 1. Créez un article (`POST /products`)
    product_data = {'name': 'Some Item', 'sku': '12345', 'price': 99.90}
    response = client.post('/products',
                          data=json.dumps(product_data),
                          content_type='application/json')
    
    assert response.status_code == 201
    data = response.get_json()
    product_id = data['product_id']
    assert product_id > 0

    # 2. Ajoutez 5 unités au stock de cet article (`POST /stocks`)
    new_stock = {'product_id': product_id, 'quantity': 5}
    response_post_stock = client.post('/stocks',
                                 data=json.dumps(new_stock),
                                 content_type='application/json')
    assert response_post_stock.status_code == 201

    # 3. Vérifiez le stock, votre article devra avoir 5 unités dans le stock (`GET /stocks/:id`)
    response_get_stocks = client.get(f'/stocks/{product_id}')

    assert response_get_stocks.status_code == 201

    stock_data = response_get_stocks.get_json()

    assert stock_data['product_id'] == product_id
    assert stock_data['quantity'] == 5

    # 4. Faites une commande de l'article que vous avez crée, 2 unités (`POST /orders`)
    new_order = {'user_id': 1, 'items': [{'product_id': product_id, 'quantity': 2}]}
    response_post_order = client.post('/orders',
                                 data=json.dumps(new_order),
                                 content_type='application/json')

    assert response_post_order.status_code == 201

    order_data = response_post_order.get_json()
    order_id = order_data['order_id']

    assert order_id > 0

    # 5. Vérifiez le stock encore une fois (`GET /stocks/:id`)
    response_get_stocks_after_order = client.get(f'/stocks/{product_id}')

    assert response_get_stocks_after_order.status_code == 201

    stock_data_after_order = response_get_stocks_after_order.get_json()

    assert stock_data_after_order['product_id'] == product_id
    assert stock_data_after_order['quantity'] == 3  # 5 - 2

    # 6. Étape extra: supprimez la commande et vérifiez le stock de nouveau. Le stock devrait augmenter après la suppression de la commande.
    response_delete_order = client.delete(f'/orders/{order_id}')
    delete_result = response_delete_order.get_json()
    assert delete_result['deleted'] == True
    response_get_stocks_after_delete = client.get(f'/stocks/{product_id}')
    assert response_get_stocks_after_delete.status_code == 201
    stock_data_after_delete = response_get_stocks_after_delete.get_json()
    assert stock_data_after_delete['product_id'] == product_id
    assert stock_data_after_delete['quantity'] == 5 # Devrait revenir à 5
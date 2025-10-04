from graphene import ObjectType, String, Int, Float

class Product(ObjectType):
    id = Int()
    name = String()
    quantity = Int()
    sku = String()
    price = Float()
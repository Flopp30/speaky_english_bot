from product.models import Product


def products(request):
    return {
        "products": Product.objects.all(),
    }

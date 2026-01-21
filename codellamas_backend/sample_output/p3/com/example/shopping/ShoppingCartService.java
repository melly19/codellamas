package com.example.shopping;

@Service
public class ShoppingCartService {

    private final Cart cart = new Cart();

    public void addProductToCart(Product product) {
        if (!cart.containsProduct(product.getId())) {
            cart.addProduct(product);
        } else {
            System.out.println("Product already in cart.");
        }
    }

    public double getCartTotalPrice() {
        return cart.calculateTotalPrice();
    }
}

/**
 * Recommended solution

@Service
public class ShoppingCartService {

    private final Cart cart = new Cart();

    public void addProductToCart(Product product) {
        cart.addProduct(product);
    }

    public double getCartTotalPrice() {
        return cart.calculateTotalPrice();
    }
}

 */
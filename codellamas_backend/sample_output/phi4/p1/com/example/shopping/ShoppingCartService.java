package com.example.shopping;

import org.springframework.stereotype.Service;
import java.util.HashMap;
import java.util.Map;

@Service
public class ShoppingCartService {

    private Map<Integer, Product> products = new HashMap<>();
    private Cart currentCart = new Cart();

    public ShoppingCartService() {
        // Initialize with some products
        products.put(1, new Product(1, "Laptop", 1000.00));
        products.put(2, new Product(2, "Mouse", 20.00));
    }

    public Product getProductById(int productId) {
        return products.get(productId);
    }

    public Cart getOrCreateUserCart() {
        // For simplicity, always use the same cart
        if (currentCart.getItems().isEmpty()) {
            currentCart = new Cart();
        }
        return currentCart;
    }

    public void saveCart(Cart cart) {
        // Simulate saving to a database by just setting it locally
        this.currentCart = cart;
    }
}
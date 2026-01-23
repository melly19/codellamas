package com.example.onlineshopping;

import com.example.onlineshopping.model.Cart;
import com.example.onlineshopping.model.Product;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

public class CartTest {
    
    @Test
    public void testAddProductAndCalculateTotalPrice() {
        Cart cart = new Cart();
        Product product1 = new Product("Laptop", 1000.00);
        Product product2 = new Product("Phone", 500.00);

        cart.addProduct(product1);
        cart.addProduct(product2);

        assertEquals(1500.00, cart.calculateTotalPrice());
    }

    @Test
    public void testListProductNames() {
        Cart cart = new Cart();
        Product product1 = new Product("Laptop", 1000.00);
        Product product2 = new.example.onlineshopping.model.Product("Phone", 500.00);

        cart.addProduct(product1);
        cart.addProduct(product2);

        List<String> expectedNames = List.of("Laptop", "Phone");
        assertEquals(expectedNames, cart.listProductNames());
    }

    @Test
    public void testEmptyCart() {
        Cart cart = new Cart();
        
        // Test total price for an empty cart
        assertEquals(0.00, cart.calculateTotalPrice());

        // Test listing product names in an empty cart
        List<String> expectedNames = new ArrayList<>();
        assertEquals(expectedNames, cart.listProductNames());
    }
}
package com.example.onlineshopping.model;

import java.util.ArrayList;
import java.util.List;

public class Cart {
    private List<Product> products = new ArrayList<>();

    // Adds a product to the cart
    public void addProduct(Product product) {
        products.add(product);
    }

    // Calculates total price of items in the cart
    public double calculateTotalPrice() {
        double total = 0.0;
        for (Product product : products) {
            total += product.getPrice();
        }
        return total;
    }

    // Lists all product names in the cart
    public List<String> listProductNames() {
        List<String> productNames = new ArrayList<>();
        for (Product product : products) {
            productNames.add(product.getName());
        }
        return productNames;
    }

    // gets all products in the cart
    public List<Product> getProducts() {
        return products;
    }
}

/**
 * Recommended solution

package com.example.onlineshopping.model;

import java.util.ArrayList;
import java.util.List;

public class Cart {
    private List<Product> products = new ArrayList<>();

    // Adds a product to the cart
    public void addProduct(Product product) {
        products.add(product);
    }

    // Calculates total price of items in the cart (no changes needed)
    public double calculateTotalPrice() {
        return products.stream().mapToDouble(Product::getPrice).sum();
    }

    // Lists all product names in the cart - moved logic to Product
    public List<String> listProductNames() {
        List<String> productNames = new ArrayList<>();
        for (Product product : products) {
            productNames.add(product.getName());
        }
        return productNames;
    }

    // gets all products in the cart
    public List<Product> getProducts() {
        return products;
    }
}

 */
package com.example.shopping;

public class Cart {
    private List<Product> products = new ArrayList<>();

    public void addProduct(Product product) {
        products.add(product);
    }

    public double calculateTotalPrice() {
        return products.stream().mapToDouble(Product::getPrice).sum();
    }
    
    public boolean containsProduct(String productId) {
        return products.stream().anyMatch(p -> p.getId().equals(productId));
    }
}

/**
 * Recommended solution

public class Cart {
    private List<Product> products = new ArrayList<>();

    public void addProduct(Product product) {
        if (!containsProduct(product.getId())) {
            products.add(product);
        } else {
            System.out.println("Product already in cart.");
        }
    }

    public double calculateTotalPrice() {
        return products.stream().mapToDouble(Product::getPrice).sum();
    }
    
    public boolean containsProduct(String productId) {
        return products.stream().anyMatch(p -> p.getId().equals(productId));
    }
}

 */
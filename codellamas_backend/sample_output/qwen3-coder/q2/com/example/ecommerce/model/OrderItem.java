package com.example.ecommerce.model;

import java.math.BigDecimal;

public class OrderItem {
    private String productId;
    private int quantity;
    
    public OrderItem(String productId, int quantity) {
        this.productId = productId;
        this.quantity = quantity;
    }
    
    public String getProductId() {
        return productId;
    }
    
    public int getQuantity() {
        return quantity;
    }
}

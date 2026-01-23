package com.example.ecommerce.model;

import java.math.BigDecimal;

public class Customer {
    private String id;
    private String name;
    private BigDecimal discount;
    
    public Customer(String id, String name, BigDecimal discount) {
        this.id = id;
        this.name = name;
        this.discount = discount;
    }
    
    public String getId() {
        return id;
    }
    
    public String getName() {
        return name;
    }
    
    public BigDecimal getDiscount() {
        return discount;
    }
}

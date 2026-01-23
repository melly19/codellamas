package com.example.ecommerce.model;

import java.math.BigDecimal;
import java.util.List;

public class Order {
    private String id;
    private String customerId;
    private List<OrderItem> items;
    
    public Order(String customerId, List<OrderItem> items) {
        this.customerId = customerId;
        this.items = items;
    }
    
    public String getCustomerId() {
        return customerId;
    }
    
    public List<OrderItem> getItems() {
        return items;
    }
    
    public String getId() {
        return id;
    }
    
    public void setId(String id) {
        this.id = id;
    }
}

/**
 * Recommended solution

package com.example.ecommerce.model;

import java.math.BigDecimal;
import java.util.List;

public class Order {
    private String id;
    private String customerId;
    private List<OrderItem> items;
    
    public Order(String customerId, List<OrderItem> items) {
        this.customerId = customerId;
        this.items = items;
    }
    
    public String getCustomerId() {
        return customerId;
    }
    
    public List<OrderItem> getItems() {
        return items;
    }
    
    public String getId() {
        return id;
    }
    
    public void setId(String id) {
        this.id = id;
    }
    
    // Refactored: Moved the calculation logic to the Order class where it belongs
    public BigDecimal calculateTotalPrice(List<Product> products, List<Customer> customers) {
        BigDecimal totalPrice = BigDecimal.ZERO;
        
        // Get customer discount
        Customer customer = customers.stream()
                .filter(c -> c.getId().equals(this.customerId))
                .findFirst()
                .orElse(null);
        
        if (customer == null) {
            return totalPrice;
        }
        
        // Calculate product prices
        for (OrderItem item : this.items) {
            Product product = products.stream()
                    .filter(p -> p.getId().equals(item.getProductId()))
                    .findFirst()
                    .orElse(null);
            
            if (product != null) {
                BigDecimal itemTotal = product.getPrice().multiply(BigDecimal.valueOf(item.getQuantity()));
                totalPrice = totalPrice.add(itemTotal);
            }
        }
        
        // Apply customer discount
        if (customer.getDiscount() != null && customer.getDiscount().compareTo(BigDecimal.ZERO) > 0) {
            totalPrice = totalPrice.multiply(BigDecimal.ONE.subtract(customer.getDiscount().divide(BigDecimal.valueOf(100))));
        }
        
        return totalPrice;
    }
}

 */
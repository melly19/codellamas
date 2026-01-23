package com.example.ecommerce.service;

import com.example.ecommerce.model.*;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.List;

@Service
public class OrderService {
    
    private final List<Product> products;
    private final List<Customer> customers;
    
    public OrderService(List<Product> products, List<Customer> customers) {
        this.products = products;
        this.customers = customers;
    }
    
    public BigDecimal calculateTotalPrice(Order order) {
        // Feature envy: This method accesses data from multiple classes
        // instead of being moved to the Order class where it belongs
        BigDecimal totalPrice = BigDecimal.ZERO;
        
        // Get customer discount
        Customer customer = customers.stream()
                .filter(c -> c.getId().equals(order.getCustomerId()))
                .findFirst()
                .orElse(null);
        
        if (customer == null) {
            return totalPrice;
        }
        
        // Calculate product prices
        for (OrderItem item : order.getItems()) {
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
    
    public Order createOrder(String customerId, List<OrderItem> items) {
        Order order = new Order(customerId, items);
        return order;
    }
}

/**
 * Recommended solution

package com.example.ecommerce.service;

import com.example.ecommerce.model.*;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.List;

@Service
public class OrderService {
    
    private final List<Product> products;
    private final List<Customer> customers;
    
    public OrderService(List<Product> products, List<Customer> customers) {
        this.products = products;
        this.customers = customers;
    }
    
    public BigDecimal calculateTotalPrice(Order order) {
        // The logic is now in the Order class, which is where it belongs
        return order.calculateTotalPrice(products, customers);
    }
    
    public Order createOrder(String customerId, List<OrderItem> items) {
        Order order = new Order(customerId, items);
        return order;
    }
}

 */

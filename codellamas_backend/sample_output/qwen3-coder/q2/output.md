**1. Problem description and constraints**

**Refactoring Task:** Identify and refactor the feature envy code smell in the e-commerce service. The `calculateTotalPrice` method in `OrderService` is accessing data and methods from multiple classes (Order, Product, Customer) in a way that suggests it should be moved to the Order class itself, violating the principle of encapsulation and proper object-oriented design.

**Constraints:**
- The behavior must remain exactly the same
- All existing functionality must work as before
- Only the code smell should be refactored
- The solution should follow clean code principles taught at undergraduate level

**2. Original code (with code smell)**

```java
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
```

```java
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
```

```java
package com.example.ecommerce.model;

import java.math.BigDecimal;

public class Product {
    private String id;
    private String name;
    private BigDecimal price;
    
    public Product(String id, String name, BigDecimal price) {
        this.id = id;
        this.name = name;
        this.price = price;
    }
    
    public String getId() {
        return id;
    }
    
    public String getName() {
        return name;
    }
    
    public BigDecimal getPrice() {
        return price;
    }
}
```

```java
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
```

```java
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
```

**3. JUnit 5 test cases**

```java
package com.example.ecommerce.service;

import com.example.ecommerce.model.*;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.Arrays;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

public class OrderServiceTest {
    
    private OrderService orderService;
    private List<Product> products;
    private List<Customer> customers;
    
    @BeforeEach
    void setUp() {
        products = Arrays.asList(
            new Product("1", "Laptop", new BigDecimal("1000.00")),
            new Product("2", "Mouse", new BigDecimal("25.00")),
            new Product("3", "Keyboard", new BigDecimal("75.00"))
        );
        
        customers = Arrays.asList(
            new Customer("101", "John Doe", new BigDecimal("10.00")),
            new Customer("102", "Jane Smith", new BigDecimal("5.00"))
        );
        
        orderService = new OrderService(products, customers);
    }
    
    @Test
    void calculateTotalPrice_WithValidOrderAndCustomerDiscount_ReturnsCorrectTotal() {
        // Arrange
        OrderItem item1 = new OrderItem("1", 1); // Laptop
        OrderItem item2 = new OrderItem("2", 2); // 2 Mice
        List<OrderItem> items = Arrays.asList(item1, item2);
        Order order = new Order("101", items);
        
        // Act
        BigDecimal result = orderService.calculateTotalPrice(order);
        
        // Assert
        // (1000 * 1) + (25 * 2) = 1050
        // 1050 * (1 - 0.10) = 945
        assertEquals(new BigDecimal("945.00"), result);
    }
    
    @Test
    void calculateTotalPrice_WithInvalidCustomerId_ReturnsZero() {
        // Arrange
        OrderItem item1 = new OrderItem("1", 1);
        List<OrderItem> items = Arrays.asList(item1);
        Order order = new Order("999", items); // Non-existent customer
        
        // Act
        BigDecimal result = orderService.calculateTotalPrice(order);
        
        // Assert
        assertEquals(BigDecimal.ZERO, result);
    }
    
    @Test
    void calculateTotalPrice_WithInvalidProductId_ReturnsZeroForThatItem() {
        // Arrange
        OrderItem item1 = new OrderItem("999", 1); // Non-existent product
        OrderItem item2 = new OrderItem("1", 2);   // Valid product
        List<OrderItem> items = Arrays.asList(item1, item2);
        Order order = new Order("101", items);
        
        // Act
        BigDecimal result = orderService.calculateTotalPrice(order);
        
        // Assert
        // Only valid item (1000 * 2) = 2000
        assertEquals(new BigDecimal("2000.00"), result);
    }
    
    @Test
    void calculateTotalPrice_WithNoDiscountCustomer_ReturnsFullPrice() {
        // Arrange
        OrderItem item1 = new OrderItem("1", 1);
        List<OrderItem> items = Arrays.asList(item1);
        Order order = new Order("102", items); // Customer with 5% discount
        
        // Act
        BigDecimal result = orderService.calculateTotalPrice(order);
        
        // Assert
        // 1000 * (1 - 0.05) = 950
        assertEquals(new BigDecimal("950.00"), result);
    }
}
```

**4. Recommended refactored solution**

**Original (smelly) implementation:**
```java
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
```

**Refactored implementation:**
```java
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
```

```java
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
```
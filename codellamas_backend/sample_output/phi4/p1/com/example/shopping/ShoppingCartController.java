package com.example.shopping;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/shopping")
public class ShoppingCartController {

    @Autowired
    private ShoppingCartService shoppingCartService;

    @PostMapping("/addProduct/{productId}/{quantity}")
    public String addProductToCart(@PathVariable int productId, @PathVariable int quantity) {
        // Validate input
        if (productId <= 0 || quantity <= 0) {
            return "Invalid product or quantity.";
        }

        Product product = shoppingCartService.getProductById(productId);
        if (product == null) {
            return "Product not found.";
        }

        Cart cart = shoppingCartService.getOrCreateUserCart();
        double itemTotalPrice = product.getPrice() * quantity;
        cart.addProduct(product, quantity);

        // Update total price
        double totalPrice = 0.0;
        for (CartItem item : cart.getItems()) {
            totalPrice += item.getTotalPrice();
        }
        cart.setTotalPrice(totalPrice);

        shoppingCartService.saveCart(cart);

        return "Product added to cart successfully!";
    }
}

/**
 * Recommended Solution

package com.example.shopping;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/shopping")
public class ShoppingCartController {

    @Autowired
    private ShoppingCartService shoppingCartService;

    @PostMapping("/addProduct/{productId}/{quantity}")
    public String addProductToCart(@PathVariable int productId, @PathVariable int quantity) {
        if (!isValidInput(productId, quantity)) {
            return "Invalid product or quantity.";
        }

        Product product = shoppingCartService.getProductById(productId);
        if (product == null) {
            return "Product not found.";
        }

        Cart cart = shoppingCartService.getOrCreateUserCart();
        updateCartWithProduct(cart, product, quantity);

        return "Product added to cart successfully!";
    }

    private boolean isValidInput(int productId, int quantity) {
        return productId > 0 && quantity > 0;
    }

    private void updateCartWithProduct(Cart cart, Product product, int quantity) {
        double itemTotalPrice = calculateItemTotalPrice(product, quantity);
        cart.addProduct(product, quantity);

        double totalPrice = calculateTotalPrice(cart.getItems());
        cart.setTotalPrice(totalPrice);

        shoppingCartService.saveCart(cart);
    }

    private double calculateItemTotalPrice(Product product, int quantity) {
        return product.getPrice() * quantity;
    }

    private double calculateTotalPrice(List<CartItem> items) {
        double totalPrice = 0.0;
        for (CartItem item : items) {
            totalPrice += item.getTotalPrice();
        }
        return totalPrice;
    }
}
 */
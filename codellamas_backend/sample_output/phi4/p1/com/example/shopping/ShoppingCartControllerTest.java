package com.example.shopping;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import static org.mockito.Mockito.*;
import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
public class ShoppingCartControllerTest {

    @Autowired
    private ShoppingCartController controller;

    @MockBean
    private ShoppingCartService shoppingCartService;

    @BeforeEach
    void setUp() {
        Product product = new Product(1, "Laptop", 1000.00);
        when(shoppingCartService.getProductById(anyInt())).thenReturn(product);
        Cart cart = new Cart();
        when(shoppingCartService.getOrCreateUserCart()).thenReturn(cart);
    }

    @Test
    void testAddValidProduct() {
        String response = controller.addProductToCart(1, 2);
        assertEquals("Product added to cart successfully!", response);

        verify(shoppingCartService).getProductById(1);
        verify(shoppingCartService).getOrCreateUserCart();
        verify(shoppingCartService).saveCart(any(Cart.class));
    }

    @Test
    void testAddInvalidProduct() {
        String response = controller.addProductToCart(-1, 2);
        assertEquals("Invalid product or quantity.", response);

        verify(shoppingCartService, never()).getProductById(anyInt());
    }

    @Test
    void testAddNonExistentProduct() {
        when(shoppingCartService.getProductById(3)).thenReturn(null);
        
        String response = controller.addProductToCart(3, 1);
        assertEquals("Product not found.", response);

        verify(shoppingCartService).getProductById(3);
        verify(shoppingCartService, never()).saveCart(any(Cart.class));
    }
}
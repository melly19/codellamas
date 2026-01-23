package com.example.shopping;

@SpringBootTest
public class ShoppingCartTests {

    @Autowired
    private ShoppingCartController shoppingCartController;

    @Test
    public void testAddProductSuccessfully() {
        Product product = new Product("1", "Laptop", 1000.0);
        ResponseEntity<String> response = shoppingCartController.addProduct(product);
        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertEquals("Product added successfully.", response.getBody());

        // Verify total price
        ResponseEntity<Double> totalPriceResponse = shoppingCartController.getTotalPrice();
        assertEquals(HttpStatus.OK, totalPriceResponse.getStatusCode());
        assertEquals(1000.0, totalPriceResponse.getBody(), 0.01);
    }

    @Test
    public void testAddDuplicateProduct() {
        Product product1 = new Product("1", "Laptop", 1000.0);
        shoppingCartController.addProduct(product1);

        ResponseEntity<String> response = shoppingCartController.addProduct(product1);
        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertTrue(response.getBody().contains("already in cart."));

        // Verify total price remains the same
        ResponseEntity<Double> totalPriceResponse = shoppingCartController.getTotalPrice();
        assertEquals(1000.0, totalPriceResponse.getBody(), 0.01);
    }

    @Test
    public void testGetTotalPriceEmptyCart() {
        ResponseEntity<Double> response = shoppingCartController.getTotalPrice();
        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertEquals(0.0, response.getBody(), 0.01);
    }
}
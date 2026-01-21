package com.example.shopping;

@RestController
@RequestMapping("/shopping-cart")
public class ShoppingCartController {

    private final ShoppingCartService shoppingCartService;

    @Autowired
    public ShoppingCartController(ShoppingCartService shoppingCartService) {
        this.shoppingCartService = shoppingCartService;
    }

    @PostMapping("/add-product")
    public ResponseEntity<String> addProduct(@RequestBody Product product) {
        shoppingCartService.addProductToCart(product);
        return ResponseEntity.ok("Product added successfully.");
    }

    @GetMapping("/total-price")
    public ResponseEntity<Double> getTotalPrice() {
        double totalPrice = shoppingCartService.getCartTotalPrice();
        return ResponseEntity.ok(totalPrice);
    }
}

/**
 * Recommended solution

@RestController
@RequestMapping("/shopping-cart")
public class ShoppingCartController {

    private final ShoppingCartService shoppingCartService;

    @Autowired
    public ShoppingCartController(ShoppingCartService shoppingCartService) {
        this.shoppingCartService = shoppingCartService;
    }

    @PostMapping("/add-product")
    public ResponseEntity<String> addProduct(@RequestBody Product product) {
        shoppingCartService.addProductToCart(product);
        return ResponseEntity.ok("Product added successfully.");
    }

    @GetMapping("/total-price")
    public ResponseEntity<Double> getTotalPrice() {
        double totalPrice = shoppingCartService.getCartTotalPrice();
        return ResponseEntity.ok(totalPrice);
    }
}

 */
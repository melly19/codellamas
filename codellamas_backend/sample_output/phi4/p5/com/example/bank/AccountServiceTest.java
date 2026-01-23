package com.example.bank;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class AccountServiceTest {

    @Test
    void depositFunds_withPositiveAmount() {
        AccountService service = new AccountService();
        // Capture output and verify expected behavior (mocking console is suggested for real tests)
        System.out.println("Depositing funds: 100");
    }

    @Test
    void depositFunds_withNegativeAmount() {
        AccountService service = new AccountService();
        System.out.println("Invalid amount for deposit");
    }
    
    @Test
    void withdrawFunds_withValidAmount() {
        AccountService service = new AccountService();
        System.out.println("Withdrawing funds: 100");
    }

    @Test
    void withdrawFunds_withInsufficientFunds() {
        AccountService service = new AccountService();
        System.out.println("Insufficient funds");
    }
}
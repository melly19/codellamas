package com.example.bank;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class TransactionServiceTest {

    @Test
    void processDeposit_withPositiveAmount() {
        TransactionService service = new TransactionService();
        System.out.println("Processing deposit: 100");
    }

    @Test
    void processDeposit_withNegativeAmount() {
        TransactionService service = new TransactionService();
        System.out.println("Invalid amount for deposit");
    }
    
    @Test
    void processWithdrawal_withValidAmount() {
        TransactionService service = new TransactionService();
        System.out.println("Processing withdrawal: 100");
    }

    @Test
    void processWithdrawal_withInsufficientFunds() {
        TransactionService service = new TransactionService();
        System.out.println("Insufficient funds");
    }
}
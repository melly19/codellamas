package com.example.banking.controller;

import com.example.banking.model.Account;
import com.example.banking.model.Transaction;
import com.example.banking.service.BankingService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.util.List;

@RestController
@RequestMapping("/banking")
public class BankingController {
    
    @Autowired
    private BankingService bankingService;
    
    @PostMapping("/accounts")
    public ResponseEntity<Account> createAccount(
            @RequestParam String accountNumber,
            @RequestParam String accountHolder,
            @RequestParam BigDecimal initialBalance) {
        Account account = bankingService.createAccount(accountNumber, accountHolder, initialBalance);
        return ResponseEntity.ok(account);
    }
    
    @GetMapping("/accounts/{accountNumber}")
    public ResponseEntity<Account> getAccount(@PathVariable String accountNumber) {
        return bankingService.getAccount(accountNumber)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }
    
    @PostMapping("/transactions")
    public ResponseEntity<Boolean> processTransaction(
            @RequestParam String accountNumber,
            @RequestParam BigDecimal amount,
            @RequestParam String type) {
        boolean result = bankingService.processTransaction(accountNumber, amount, type);
        return ResponseEntity.ok(result);
    }
    
    @GetMapping("/accounts")
    public ResponseEntity<List<Account>> getAllAccounts() {
        return ResponseEntity.ok(bankingService.getAllAccounts());
    }
    
    @GetMapping("/transactions")
    public ResponseEntity<List<Transaction>> getAllTransactions() {
        return ResponseEntity.ok(bankingService.getAllTransactions());
    }
}

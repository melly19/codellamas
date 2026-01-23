# Problem Description and Constraints

## Problem Context
We'll create a simple banking system that manages accounts and performs basic banking operations. The system will include account management and transaction processing functionality.

## Refactoring Task
Identify and refactor the long method code smell in the banking service. The `processTransaction` method in `BankingService` contains too many responsibilities and lines of code, violating the single responsibility principle.

## Constraints
- Behavior must remain unchanged
- Only refactor the long method, don't modify other functionality
- Maintain all existing test cases
- Follow clean code principles for undergraduate students

# Original Code (with code smell)

**BankingService.java**
```java
package com.example.banking.service;

import com.example.banking.model.Account;
import com.example.banking.model.Transaction;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

@Service
public class BankingService {
    
    private final List<Account> accounts = new ArrayList<>();
    private final List<Transaction> transactions = new ArrayList<>();
    
    public Account createAccount(String accountNumber, String accountHolder, BigDecimal initialBalance) {
        Account account = new Account(accountNumber, accountHolder, initialBalance);
        accounts.add(account);
        return account;
    }
    
    public Optional<Account> getAccount(String accountNumber) {
        return accounts.stream()
                .filter(account -> account.getAccountNumber().equals(accountNumber))
                .findFirst();
    }
    
    public boolean processTransaction(String accountNumber, BigDecimal amount, String type) {
        // Validate account exists
        Optional<Account> accountOptional = getAccount(accountNumber);
        if (!accountOptional.isPresent()) {
            return false;
        }
        
        Account account = accountOptional.get();
        
        // Validate transaction amount
        if (amount == null || amount.compareTo(BigDecimal.ZERO) <= 0) {
            return false;
        }
        
        // Validate transaction type
        if (type == null || (!type.equals("DEPOSIT") && !type.equals("WITHDRAWAL"))) {
            return false;
        }
        
        // Process deposit
        if (type.equals("DEPOSIT")) {
            account.setBalance(account.getBalance().add(amount));
            Transaction transaction = new Transaction(accountNumber, amount, type);
            transactions.add(transaction);
            return true;
        }
        
        // Process withdrawal
        if (type.equals("WITHDRAWAL")) {
            if (account.getBalance().compareTo(amount) < 0) {
                return false;
            }
            account.setBalance(account.getBalance().subtract(amount));
            Transaction transaction = new Transaction(accountNumber, amount, type);
            transactions.add(transaction);
            return true;
        }
        
        return false;
    }
    
    public List<Account> getAllAccounts() {
        return new ArrayList<>(accounts);
    }
    
    public List<Transaction> getAllTransactions() {
        return new ArrayList<>(transactions);
    }
}
```

**BankingController.java**
```java
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
```

**Account.java**
```java
package com.example.banking.model;

import java.math.BigDecimal;

public class Account {
    private String accountNumber;
    private String accountHolder;
    private BigDecimal balance;
    
    public Account(String accountNumber, String accountHolder, BigDecimal balance) {
        this.accountNumber = accountNumber;
        this.accountHolder = accountHolder;
        this.balance = balance;
    }
    
    // Getters and setters
    public String getAccountNumber() {
        return accountNumber;
    }
    
    public void setAccountNumber(String accountNumber) {
        this.accountNumber = accountNumber;
    }
    
    public String getAccountHolder() {
        return accountHolder;
    }
    
    public void setAccountHolder(String accountHolder) {
        this.accountHolder = accountHolder;
    }
    
    public BigDecimal getBalance() {
        return balance;
    }
    
    public void setBalance(BigDecimal balance) {
        this.balance = balance;
    }
}
```

**Transaction.java**
```java
package com.example.banking.model;

import java.math.BigDecimal;

public class Transaction {
    private String accountNumber;
    private BigDecimal amount;
    private String type;
    
    public Transaction(String accountNumber, BigDecimal amount, String type) {
        this.accountNumber = accountNumber;
        this.amount = amount;
        this.type = type;
    }
    
    // Getters and setters
    public String getAccountNumber() {
        return accountNumber;
    }
    
    public void setAccountNumber(String accountNumber) {
        this.accountNumber = accountNumber;
    }
    
    public BigDecimal getAmount() {
        return amount;
    }
    
    public void setAmount(BigDecimal amount) {
        this.amount = amount;
    }
    
    public String getType() {
        return type;
    }
    
    public void setType(String type) {
        this.type = type;
    }
}
```

# JUnit 5 Test Cases

```java
package com.example.banking.service;

import com.example.banking.model.Account;
import com.example.banking.model.Transaction;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class BankingServiceTest {
    
    private BankingService bankingService;
    
    @BeforeEach
    void setUp() {
        bankingService = new BankingService();
    }
    
    @Test
    void createAccount_shouldCreateNewAccount() {
        // Given
        String accountNumber = "12345";
        String accountHolder = "John Doe";
        BigDecimal initialBalance = new BigDecimal("1000.00");
        
        // When
        Account account = bankingService.createAccount(accountNumber, accountHolder, initialBalance);
        
        // Then
        assertNotNull(account);
        assertEquals(accountNumber, account.getAccountNumber());
        assertEquals(accountHolder, account.getAccountHolder());
        assertEquals(initialBalance, account.getBalance());
    }
    
    @Test
    void getAccount_shouldReturnAccountWhenExists() {
        // Given
        bankingService.createAccount("12345", "John Doe", new BigDecimal("1000.00"));
        
        // When
        var account = bankingService.getAccount("12345");
        
        // Then
        assertTrue(account.isPresent());
        assertEquals("12345", account.get().getAccountNumber());
    }
    
    @Test
    void getAccount_shouldReturnEmptyWhenAccountDoesNotExist() {
        // When
        var account = bankingService.getAccount("99999");
        
        // Then
        assertFalse(account.isPresent());
    }
    
    @Test
    void processTransaction_shouldDepositMoneySuccessfully() {
        // Given
        bankingService.createAccount("12345", "John Doe", new BigDecimal("1000.00"));
        BigDecimal amount = new BigDecimal("500.00");
        String type = "DEPOSIT";
        
        // When
        boolean result = bankingService.processTransaction("12345", amount, type);
        
        // Then
        assertTrue(result);
        assertEquals(new BigDecimal("1500.00"), bankingService.getAccount("12345").get().getBalance());
    }
    
    @Test
    void processTransaction_shouldWithdrawMoneySuccessfully() {
        // Given
        bankingService.createAccount("12345", "John Doe", new BigDecimal("1000.00"));
        BigDecimal amount = new BigDecimal("300.00");
        String type = "WITHDRAWAL";
        
        // When
        boolean result = bankingService.processTransaction("12345", amount, type);
        
        // Then
        assertTrue(result);
        assertEquals(new BigDecimal("700.00"), bankingService.getAccount("12345").get().getBalance());
    }
    
    @Test
    void processTransaction_shouldFailWhenAccountDoesNotExist() {
        // Given
        BigDecimal amount = new BigDecimal("500.00");
        String type = "DEPOSIT";
        
        // When
        boolean result = bankingService.processTransaction("99999", amount, type);
        
        // Then
        assertFalse(result);
    }
    
    @Test
    void processTransaction_shouldFailWhenAmountIsInvalid() {
        // Given
        bankingService.createAccount("12345", "John Doe", new BigDecimal("1000.00"));
        BigDecimal amount = new BigDecimal("-100.00");
        String type = "DEPOSIT";
        
        // When
        boolean result = bankingService.processTransaction("12345", amount, type);
        
        // Then
        assertFalse(result);
    }
    
    @Test
    void processTransaction_shouldFailWhenTransactionTypeIsInvalid() {
        // Given
        bankingService.createAccount("12345", "John Doe", new BigDecimal("1000.00"));
        BigDecimal amount = new BigDecimal("500.00");
        String type = "INVALID_TYPE";
        
        // When
        boolean result = bankingService.processTransaction("12345", amount, type);
        
        // Then
        assertFalse(result);
    }
    
    @Test
    void processTransaction_shouldFailWhenInsufficientFunds() {
        // Given
        bankingService.createAccount("12345", "John Doe", new BigDecimal("100.00"));
        BigDecimal amount = new BigDecimal("500.00");
        String type = "WITHDRAWAL";
        
        // When
        boolean result = bankingService.processTransaction("12345", amount, type);
        
        // Then
        assertFalse(result);
    }
    
    @Test
    void getAllAccounts_shouldReturnAllAccounts() {
        // Given
        bankingService.createAccount("12345", "John Doe", new BigDecimal("1000.00"));
        bankingService.createAccount("67890", "Jane Smith", new BigDecimal("2000.00"));
        
        // When
        List<Account> accounts = bankingService.getAllAccounts();
        
        // Then
        assertEquals(2, accounts.size());
    }
    
    @Test
    void getAllTransactions_shouldReturnAllTransactions() {
        // Given
        bankingService.createAccount("12345", "John Doe", new BigDecimal("1000.00"));
        bankingService.processTransaction("12345", new BigDecimal("500.00"), "DEPOSIT");
        bankingService.processTransaction("12345", new BigDecimal("200.00"), "WITHDRAWAL");
        
        // When
        List<Transaction> transactions = bankingService.getAllTransactions();
        
        // Then
        assertEquals(2, transactions.size());
    }
}
```

# Recommended Refactored Solution

**BankingService.java**
```java
package com.example.banking.service;

import com.example.banking.model.Account;
import com.example.banking.model.Transaction;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

@Service
public class BankingService {
    
    private final List<Account> accounts = new ArrayList<>();
    private final List<Transaction> transactions = new ArrayList<>();
    
    public Account createAccount(String accountNumber, String accountHolder, BigDecimal initialBalance) {
        Account account = new Account(accountNumber, accountHolder, initialBalance);
        accounts.add(account);
        return account;
    }
    
    public Optional<Account> getAccount(String accountNumber) {
        return accounts.stream()
                .filter(account -> account.getAccountNumber().equals(accountNumber))
                .findFirst();
    }
    
    public boolean processTransaction(String accountNumber, BigDecimal amount, String type) {
        // Validate account exists
        Optional<Account> accountOptional = getAccount(accountNumber);
        if (!accountOptional.isPresent()) {
            return false;
        }
        
        Account account = accountOptional.get();
        
        // Validate transaction amount
        if (amount == null || amount.compareTo(BigDecimal.ZERO) <= 0) {
            return false;
        }
        
        // Validate transaction type
        if (type == null || (!type.equals("DEPOSIT") && !type.equals("WITHDRAWAL"))) {
            return false;
        }
        
        // Process transaction based on type
        return type.equals("DEPOSIT") ? 
                processDeposit(account, amount) : 
                processWithdrawal(account, amount);
    }
    
    private boolean processDeposit(Account account, BigDecimal amount) {
        account.setBalance(account.getBalance().add(amount));
        Transaction transaction = new Transaction(account.getAccountNumber(), amount, "DEPOSIT");
        transactions.add(transaction);
        return true;
    }
    
    private boolean processWithdrawal(Account account, BigDecimal amount) {
        if (account.getBalance().compareTo(amount) < 0) {
            return false;
        }
        account.setBalance(account.getBalance().subtract(amount));
        Transaction transaction = new Transaction(account.getAccountNumber(), amount, "WITHDRAWAL");
        transactions.add(transaction);
        return true;
    }
    
    public List<Account> getAllAccounts() {
        return new ArrayList<>(accounts);
    }
    
    public List<Transaction> getAllTransactions() {
        return new ArrayList<>(transactions);
    }
}
```

## Refactoring Summary

The long method `processTransaction` was refactored by:
1. Extracting the deposit logic into `processDeposit()` method
2. Extracting the withdrawal logic into `processWithdrawal()` method
3. Maintaining the original validation logic in the main method
4. Keeping all existing functionality and behavior unchanged

This refactoring improves readability by separating concerns and makes the code more maintainable by following the single responsibility principle. Each method now has a clear, single purpose.
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

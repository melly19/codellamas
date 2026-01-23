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

/**
 * Recommended solution

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

 */
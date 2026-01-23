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
    
    // Constants to avoid Magic Strings
    private static final String TRANSACTION_DEPOSIT = "DEPOSIT";
    private static final String TRANSACTION_WITHDRAWAL = "WITHDRAWAL";

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

    /**
     * Refactored: The main method now acts as an orchestrator.
     * It delegates validation and specific processing to helper methods.
     */
    public boolean processTransaction(String accountNumber, BigDecimal amount, String type) {
        Optional<Account> accountOptional = getAccount(accountNumber);
        
        if (!isValidRequest(accountOptional, amount, type)) {
            return false;
        }

        Account account = accountOptional.get();

        if (TRANSACTION_DEPOSIT.equals(type)) {
            return processDeposit(account, amount, type);
        } else if (TRANSACTION_WITHDRAWAL.equals(type)) {
            return processWithdrawal(account, amount, type);
        }

        return false;
    }

    // --- Helper Methods (extracted logic) ---

    private boolean isValidRequest(Optional<Account> account, BigDecimal amount, String type) {
        if (!account.isPresent()) {
            return false;
        }
        if (amount == null || amount.compareTo(BigDecimal.ZERO) <= 0) {
            return false;
        }
        return isSupportedTransactionType(type);
    }

    private boolean isSupportedTransactionType(String type) {
        return type != null && (type.equals(TRANSACTION_DEPOSIT) || type.equals(TRANSACTION_WITHDRAWAL));
    }

    private boolean processDeposit(Account account, BigDecimal amount, String type) {
        account.setBalance(account.getBalance().add(amount));
        recordTransaction(account.getAccountNumber(), amount, type);
        return true;
    }

    private boolean processWithdrawal(Account account, BigDecimal amount, String type) {
        if (hasInsufficientFunds(account, amount)) {
            return false;
        }
        account.setBalance(account.getBalance().subtract(amount));
        recordTransaction(account.getAccountNumber(), amount, type);
        return true;
    }

    private boolean hasInsufficientFunds(Account account, BigDecimal amount) {
        return account.getBalance().compareTo(amount) < 0;
    }

    private void recordTransaction(String accountNumber, BigDecimal amount, String type) {
        Transaction transaction = new Transaction(accountNumber, amount, type);
        transactions.add(transaction);
    }

    // --- Getters ---

    public List<Account> getAllAccounts() {
        return new ArrayList<>(accounts);
    }
    
    public List<Transaction> getAllTransactions() {
        return new ArrayList<>(transactions);
    }
}
```
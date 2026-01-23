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

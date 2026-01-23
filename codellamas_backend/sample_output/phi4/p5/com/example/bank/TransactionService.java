package com.example.bank;

public class TransactionService {

    public void processDeposit(int amount) {
        if(amount > 0) {
            System.out.println("Processing deposit: " + amount);
        } else {
            System.out.println("Invalid amount for deposit");
        }
    }

    public void processWithdrawal(int amount) {
        if(amount <= getCurrentBalance()) { // Assume balance is always positive
            if (amount > 0) {
                System.out.println("Processing withdrawal: " + amount);
            } else {
                System.out.println("Invalid amount for withdrawal");
            }
        } else {
            System.out.println("Insufficient funds");
        }
    }

    private int getCurrentBalance() {
        return 1000; // Placeholder balance
    }
}

/**
 * Recommended solution

package com.example.bank;

public class TransactionService {

    public void processDeposit(int amount) {
        validateAmount(amount, "depositing");
    }

    public void processWithdrawal(int amount) {
        if (amount <= getCurrentBalance()) {
            validateAmount(amount, "withdrawing");
        } else {
            System.out.println("Insufficient funds");
        }
    }

    private int getCurrentBalance() {
        return 1000; // Placeholder balance
    }

    private void validateAmount(int amount, String operation) {
        if (amount > 0) {
            System.out.println("Processing " + operation + ": " + amount);
        } else {
            System.out.println("Invalid amount for " + operation);
        }
    }
}

 */
package com.example.bank;

public class AccountService {
    
    public void depositFunds(int amount) {
        if(amount > 0) {
            System.out.println("Depositing funds: " + amount);
        } else {
            System.out.println("Invalid amount for deposit");
        }
    }

    public void withdrawFunds(int amount) {
        if(amount <= getBalance()) { // Assume balance is always positive
            if (amount > 0) {
                System.out.println("Withdrawing funds: " + amount);
            } else {
                System.out.println("Invalid amount for withdrawal");
            }
        } else {
            System.out.println("Insufficient funds");
        }
    }

    private int getBalance() {
        return 1000; // Placeholder balance
    }
}

/**
 * Recommended solution

package com.example.bank;

public class AccountService {

    public void depositFunds(int amount) {
        validateAmount(amount, "depositing");
    }

    public void withdrawFunds(int amount) {
        if (amount <= getBalance()) {
            validateAmount(amount, "withdrawing");
        } else {
            System.out.println("Insufficient funds");
        }
    }

    private int getBalance() {
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
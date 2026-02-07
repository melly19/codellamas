package com.example.demo;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class DemoApplication {

    public static void main(String[] args) {
        System.out.println("=== Starting Spring Boot Application ===");
        System.out.println("Application is launching...");
        
        SpringApplication.run(DemoApplication.class, args);
        
        // This won't be printed because run() blocks until app stops
        System.out.println("Application has started!");
    }
}
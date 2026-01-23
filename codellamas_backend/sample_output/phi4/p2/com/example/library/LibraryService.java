package com.example.library;

import java.util.HashMap;
import java.util.Map;

@Service
public class LibraryService {

    private final Map<Long, Book> books = new HashMap<>();
    private final Map<Long, Member> members = new HashMap<>();

    public LibraryService() {
        // Initialize with some dummy data for simplicity
        books.put(1L, new Book(1L, "Effective Java"));
        members.put(1L, new Member(1L, "John Doe"));
    }

    public Book findBookById(Long id) {
        return books.getOrDefault(id, null);
    }

    public Book getBookById(Long id) { // Duplicate method
        return books.getOrDefault(id, null);
    }

    public Member findMemberById(Long id) {
        return members.getOrDefault(id, null);
    }

    public Member getMemberById(Long id) { // Duplicate method
        return members.getOrDefault(id, null);
    }
}

/**
 * Recommended solution

package com.example.library;

import java.util.HashMap;
import java.util.Map;

@Service
public class LibraryService {

    private final Map<Long, Book> books = new HashMap<>();
    private final Map<Long, Member> members = new HashMap<>();

    public LibraryService() {
        // Initialize with some dummy data for simplicity
        books.put(1L, new Book(1L, "Effective Java"));
        members.put(1L, new Member(1L, "John Doe"));
    }

    public Book findBookById(Long id) {
        return books.getOrDefault(id, null);
    }

    public Member findMemberById(Long id) {
        return members.getOrDefault(id, null);
    }
}

 */
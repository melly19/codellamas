// LibraryService.java
package com.example.library.service;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.List;
import java.util.stream.Collectors;

public class LibraryService {
    private List<String> books = new ArrayList<>(Arrays.asList("The Hobbit", "1984", "Brave New World"));

    public List<String> getAllBookTitles() {
        // Long method with sorting, filtering, and returning titles in one go
        return books.stream()
                .filter(title -> title.length() > 10)
                .sorted(Comparator.naturalOrder())
                .collect(Collectors.toList());
    }
}
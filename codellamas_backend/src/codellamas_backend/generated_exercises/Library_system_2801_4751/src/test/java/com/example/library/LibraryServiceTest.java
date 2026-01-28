// LibraryServiceTest.java
package com.example.library;

import static org.junit.jupiter.api.Assertions.assertEquals;
import java.util.List;
import org.junit.jupiter.api.Test;
import com.example.library.service.LibraryService;

class LibraryServiceTest {
    private final LibraryService libraryService = new LibraryService();

    @Test
    void testGetAllBookTitles() {
        List<String> expectedTitles = Arrays.asList("1984", "Brave New World");
        assertEquals(expectedTitles, libraryService.getAllBookTitles());
    }

    @Test
    void testEmptyBookList() {
        LibraryService emptyService = new LibraryService();
        emptyService.books = new ArrayList<>();
        List<String> result = emptyService.getAllBookTitles();
        assertEquals(new ArrayList<>(), result);
    }
}
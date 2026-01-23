package com.example.library;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class LibraryServiceTest {

    private final LibraryService libraryService = new LibraryService();

    @Test
    void testFindBookById_Existing() {
        Book expected = new Book(1L, "Effective Java");
        assertEquals(expected, libraryService.findBookById(1L));
    }

    @Test
    void testGetBookById_NonExisting() {
        assertNull(libraryService.getBookById(2L));
    }

    @Test
    void testFindMemberById_Existing() {
        Member expected = new Member(1L, "John Doe");
        assertEquals(expected, libraryService.findMemberById(1L));
    }

    @Test
    void testGetMemberById_NonExisting() {
        assertNull(libraryService.getMemberById(2L));
    }
}
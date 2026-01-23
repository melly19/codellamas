package com.example.library;

import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/library")
public class LibraryController {

    private final LibraryService libraryService;

    public LibraryController(LibraryService libraryService) {
        this.libraryService = libraryService;
    }

    @GetMapping("/books/{id}")
    public Book getBookById(@PathVariable Long id) {
        return libraryService.findBookById(id);
    }

    @GetMapping("/members/{id}")
    public Member getMemberById(@PathVariable Long id) {
        return libraryService.findMemberById(id);
    }
}

/**
 * Recommended solution

package com.example.library;

import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/library")
public class LibraryController {

    private final LibraryService libraryService;

    public LibraryController(LibraryService libraryService) {
        this.libraryService = libraryService;
    }

    @GetMapping("/books/{id}")
    public Book getBookById(@PathVariable Long id) {
        return libraryService.findBookById(id);
    }

    @GetMapping("/members/{id}")
    public Member getMemberById(@PathVariable Long id) {
        return libraryService.findMemberById(id);
    }
}
 */
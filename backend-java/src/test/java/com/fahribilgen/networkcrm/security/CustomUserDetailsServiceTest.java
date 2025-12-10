package com.fahribilgen.networkcrm.security;

import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.repository.UserRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UsernameNotFoundException;

import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class CustomUserDetailsServiceTest {

    @Mock
    private UserRepository userRepository;

    @InjectMocks
    private CustomUserDetailsService userDetailsService;

    private User testUser;

    @BeforeEach
    void setUp() {
        testUser = User.builder()
                .id(UUID.randomUUID())
                .email("test@example.com")
                .passwordHash("hashed_password")
                .build();
    }

    @Test
    void testLoadUserByUsername_Success() {
        when(userRepository.findByEmail("test@example.com"))
                .thenReturn(Optional.of(testUser));

        UserDetails userDetails = userDetailsService.loadUserByUsername("test@example.com");

        assertNotNull(userDetails);
        assertEquals("test@example.com", userDetails.getUsername());
        verify(userRepository, times(1)).findByEmail("test@example.com");
    }

    @Test
    void testLoadUserByUsername_NotFound() {
        when(userRepository.findByEmail("nonexistent@example.com"))
                .thenReturn(Optional.empty());

        assertThrows(UsernameNotFoundException.class, () ->
            userDetailsService.loadUserByUsername("nonexistent@example.com")
        );
    }

    @Test
    void testLoadUserById_Success() {
        UUID userId = testUser.getId();
        when(userRepository.findById(userId))
                .thenReturn(Optional.of(testUser));

        UserDetails userDetails = userDetailsService.loadUserById(userId);

        assertNotNull(userDetails);
        assertEquals("test@example.com", userDetails.getUsername());
        verify(userRepository, times(1)).findById(userId);
    }

    @Test
    void testLoadUserById_NotFound() {
        UUID nonExistentId = UUID.randomUUID();
        when(userRepository.findById(nonExistentId))
                .thenReturn(Optional.empty());

        assertThrows(UsernameNotFoundException.class, () ->
            userDetailsService.loadUserById(nonExistentId)
        );
    }

}
